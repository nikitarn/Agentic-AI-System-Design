import pickle
from pathlib import Path

import chromadb
from langchain_core.documents import Document
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter
from rank_bm25 import BM25Okapi

from financial_analyst.config import config
from financial_analyst.llm.factory import get_embedder
from financial_analyst.observability.logger import get_logger

logger = get_logger(__name__)

DOCS_DIR = Path(__file__).parent / "docs"
CHUNKS_CACHE_PATH = Path(__file__).parent / "chunks_cache.pkl"

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100


def load_docs(docs_dir: Path = DOCS_DIR) -> list[Document]:
    """Load every markdown file under docs_dir (including subfolders) as a Document."""
    docs = []
    for path in sorted(docs_dir.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        docs.append(Document(
            page_content=text,
            metadata={"source": str(path.relative_to(docs_dir))},
        ))
    return docs


def chunk_docs(docs: list[Document]) -> list[Document]:
    """Markdown-aware chunking so splits happen on header/paragraph boundaries."""
    splitter = RecursiveCharacterTextSplitter.from_language(
        language=Language.MARKDOWN,
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    return splitter.split_documents(docs)


def load_or_chunk_docs(docs_dir: Path = DOCS_DIR) -> list[Document]:
    """Load + chunk markdown docs, cached to disk so restarts skip re-chunking."""
    if CHUNKS_CACHE_PATH.exists():
        with open(CHUNKS_CACHE_PATH, "rb") as f:
            chunks = pickle.load(f)
        logger.info(f"Loaded {len(chunks)} cached chunks from {CHUNKS_CACHE_PATH}")
        return chunks

    docs = load_docs(docs_dir)
    chunks = chunk_docs(docs)
    logger.info(f"Loaded {len(docs)} docs -> {len(chunks)} chunks (chunk_size={CHUNK_SIZE})")

    with open(CHUNKS_CACHE_PATH, "wb") as f:
        pickle.dump(chunks, f)
    return chunks


def build_semantic_index(chunks: list[Document]) -> chromadb.Collection:
    """Embed chunks and upsert into the persistent Chroma collection. Skips if already populated."""
    client = chromadb.PersistentClient(path=config["chromadb"]["persist_dir"])
    collection = client.get_or_create_collection(name=config["chromadb"]["collection_name"])

    if collection.count() > 0:
        logger.info(f"Loaded existing semantic index with {collection.count()} chunks")
        return collection

    embedder = get_embedder()
    logger.info(f"Building semantic index over {len(chunks)} chunks")
    for i, chunk in enumerate(chunks):
        embedding = embedder.embed_query(chunk.page_content)
        doc_id = f"{chunk.metadata['source']}::{i}"
        collection.upsert(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[chunk.page_content],
            metadatas=[chunk.metadata],
        )
    logger.info(f"Semantic index complete. Total chunks: {collection.count()}")
    return collection


def build_lexical_index(chunks: list[Document]) -> BM25Okapi:
    """Build a BM25 index over the given chunks (cheap, no external calls — rebuilt each run)."""
    tokenized = [chunk.page_content.lower().split() for chunk in chunks]
    return BM25Okapi(tokenized)


def build_indexes(docs_dir: Path = DOCS_DIR) -> tuple[chromadb.Collection, BM25Okapi, list[Document]]:
    """Build (or load) both the semantic (Chroma) and lexical (BM25) indexes."""
    chunks = load_or_chunk_docs(docs_dir)
    collection = build_semantic_index(chunks)
    bm25 = build_lexical_index(chunks)
    return collection, bm25, chunks


def show_index(collection: chromadb.Collection) -> None:
    """Display all documents stored in the Chroma collection."""
    from rich.console import Console
    console = Console()
    results = collection.get(include=["documents", "metadatas"])
    console.print(f"\n[bold]Semantic Index — {collection.count()} chunks[/bold]\n")
    for i, (doc, meta) in enumerate(zip(results["documents"], results["metadatas"])):
        console.print(f"[bold cyan]── Chunk {i + 1} ──────────────────────────[/bold cyan]")
        console.print(f"  Source : {meta.get('source')}")
        console.print(f"  Text   :\n[dim]{doc[:300]}[/dim]\n")


if __name__ == "__main__":
    collection, bm25, chunks = build_indexes()
    show_index(collection)
    print(f"\nBM25 index built over {len(chunks)} chunks (in-memory, not persisted)")
