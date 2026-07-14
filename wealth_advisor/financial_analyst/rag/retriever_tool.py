import chromadb
from langchain.agents import create_agent
from langchain.tools import tool
from rank_bm25 import BM25Okapi
from langchain_core.documents import Document

from financial_analyst.knowledge_base.indexer import build_indexes
from financial_analyst.llm.factory import get_embedder, get_llm
from financial_analyst.observability.logger import get_logger

logger = get_logger(__name__)

TOP_K = 4

# ---------------------------------------------------------------------------
# retrieval_tool (outer @tool)
#     |_ router agent (create_agent)
#             |_ semantic_retrieval  - dense vector search via Chroma
#             |_ lexical_retrieval   - sparse BM25 keyword search
#
# The router agent receives the user query and decides which sub-tool(s)
# to call. The main financial-advisor agent only ever sees retrieval_tool
# and delegates all retrieval decisions to it.
# ---------------------------------------------------------------------------


def build_retrieval_tool(collection: chromadb.Collection, bm25: BM25Okapi, chunks: list[Document]):
    embedder = get_embedder()
    llm = get_llm()

    @tool
    def semantic_retrieval(query: str) -> str:
        """Retrieve knowledge base passages using dense vector (semantic) similarity.
        Use for conceptual queries — e.g. "what's a good low-risk fund for a 3-year goal",
        "how does SEBI categorize mutual funds", "how is LTCG taxed on equity funds"."""
        embedding = embedder.embed_query(query)
        results = collection.query(query_embeddings=[embedding], n_results=TOP_K)
        docs = results["documents"][0]
        metadatas = results["metadatas"][0]
        logger.info(f"[semantic_retrieval] '{query}' -> {len(docs)} chunks")
        return "\n\n".join(
            f"# {meta.get('source', 'unknown')}\n{doc}" for doc, meta in zip(docs, metadatas)
        )

    @tool
    def lexical_retrieval(query: str) -> str:
        """Retrieve knowledge base passages using BM25 keyword matching.
        Use for exact terms — ticker/scheme codes (e.g. "AXISBLUECHIP", "NSE:INFY"),
        section numbers (e.g. "Section 80C"), or other identifiers unlikely to embed well."""
        tokens = query.lower().split()
        scores = bm25.get_scores(tokens)
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:TOP_K]
        docs = [chunks[i] for i in top_indices]
        logger.info(f"[lexical_retrieval] '{query}' -> {len(docs)} chunks")
        return "\n\n".join(
            f"# {d.metadata.get('source', 'unknown')}\n{d.page_content}" for d in docs
        )

    router_agent = create_agent(
        model=llm,
        tools=[semantic_retrieval, lexical_retrieval],
        system_prompt=(
            "You are a retrieval router for a personal-finance knowledge base "
            "(mutual funds, stock symbols, SEBI/RBI rules, tax rules, retirement/SIP guidance). "
            "Given a query, call the right retrieval tool(s):\n"
            "- semantic_retrieval: conceptual or intent-based questions\n"
            "- lexical_retrieval: exact fund/ticker codes, section numbers, or other identifiers\n"
            "Call both if the query mixes a concept with a specific identifier. "
            "Return all retrieved content without summarising it."
        ),
    )

    @tool
    def retrieval_tool(query: str) -> str:
        """Retrieve relevant passages from the financial knowledge base for any question.
        Internally routes to semantic or lexical retrieval (or both) as appropriate."""
        logger.info(f"[retrieval_tool] Routing query: '{query}'")
        result = router_agent.invoke({"messages": [{"role": "user", "content": query}]})
        return str(result["messages"][-1].content)

    return retrieval_tool


def get_retrieval_tool():
    """Build (or load) the indexes and return the ready-to-use retrieval_tool."""
    collection, bm25, chunks = build_indexes()
    return build_retrieval_tool(collection, bm25, chunks)
