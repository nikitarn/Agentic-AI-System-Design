import os
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.prompt import Prompt
import chromadb


from claude_project.config import config
from claude_project.context.indexers.semantic_chroma import index_codebase
from claude_project.llm.factory import get_llm, get_embedder
from claude_project.observability.logging import get_logger


# Load .env before anything else
load_dotenv()
console = Console()
logger = get_logger(__name__)


def get_or_create_index() -> chromadb.Collection:
 """Load existing index or create a new one by indexing current directory."""
 chroma_client = chromadb.PersistentClient(path=config["chromadb"]["persist_dir"])
 collection = chroma_client.get_or_create_collection(name=config["chromadb"]["collection_name"])


 if collection.count() > 0:
     logger.info(f"Loaded existing index with {collection.count()} chunks")
     console.print(f"[dim]Loaded existing index — {collection.count()} chunks[/dim]")
     return collection


 # Auto-index the current working directory
 repo_path = str(Path.cwd())
 logger.info(f"Indexing repo: {repo_path}")
 console.print(f"[dim]Indexing {repo_path}...[/dim]")
 return index_codebase(repo_path)


def show_semantic_index(collection: chromadb.Collection) -> None:
 """Display all documents stored in the ChromaDB collection."""
 results = collection.get(include=["documents", "metadatas", "embeddings"])
 console.print(f"\n[bold]Semantic Index — {collection.count()} chunks[/bold]\n")


 for i, (doc, meta, emb) in enumerate(zip(
     results["documents"],
     results["metadatas"],
     results["embeddings"]
 )):
     console.print(f"[bold cyan]── Chunk {i+1} ──────────────────────────[/bold cyan]")
     console.print(f"  File     : {meta['source']}")
     console.print(f"  Name     : {meta['name']} ({meta['type']})")
     console.print(f"  Lines    : {meta['start_line']} - {meta['end_line']}")
     console.print(f"  Embedding: [{', '.join(f'{v:.4f}' for v in emb[:5])}...] ({len(emb)} dims)")
     console.print(f"  Code     :\n[dim]{doc[:300]}[/dim]\n")




def initialize():
 """Bootstrap LLM, embedder, and index before the REPL starts."""
 llm = get_llm()
 embedder = get_embedder()
 console.print(f"[dim]LLM: {config['llm']['provider']} / {config['llm']['model']}[/dim]")
 console.print(f"[dim]Embedder: {config['embeddings']['provider']} / {config['embeddings']['model']}[/dim]")


 collection = get_or_create_index()
 console.print(f"[green]✓ Ready — {collection.count()} chunks indexed[/green]\n")
 return llm, embedder, collection


def run():
 logger.info("Starting Educosys Claude")
 console.print("\n[bold blue]Educosys Claude[/bold blue] — RAG-powered code assistant")


 llm, embedder, collection = initialize()
 console.print("Type [bold]'/exit'[/bold] to quit\n")


 while True:
     user_input = Prompt.ask("[bold green]>[/bold green]")


     if not user_input.strip():
         continue
     if user_input.lower() in ("/exit", "/quit"):
         logger.info("Shutting down")
         console.print("[dim]Goodbye![/dim]")
         break
     elif user_input.startswith("/ask "):
         question = user_input.removeprefix("/ask ").strip()
         logger.info(f"Ask command received: {question}")
         console.print(f"[dim]Searching for: {question}...[/dim]")
         # TODO: call retriever + LLM
     elif user_input == "/show_semantic_index":
         logger.info("Showing semantic index")
         show_semantic_index(collection)
     else:
         logger.warning(f"Unknown command received: {user_input}")
         console.print("[yellow]Unknown command. Try:[/yellow]")
         console.print("  [bold]ask <question>[/bold]       — ask a question about the codebase")
         console.print("  [bold]show_semantic_index[/bold]  — show all chunks in the semantic index")


if __name__ == "__main__":
 run()
