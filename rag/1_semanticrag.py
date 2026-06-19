from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.messages import ChatMessage, SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.tools.retriever import create_retriever_tool
from langchain.agents import create_agent
from pathlib import Path
from langchain.agents.middleware import ToolCallLimitMiddleware, ModelCallLimitMiddleware
import os

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHUNK_SIZE = 256
CHUNK_OVERLAP = 32


def load_all_docs(repo_path):
    docs = []

    print(f"Loading documents from {repo_path}...")

    for path in Path(repo_path).rglob("*.py"):
        if path.is_file():
            # Ensure we can read the file
            content = path.read_text(encoding="utf-8", errors="ignore")

            docs.append(Document(page_content=content,
                        metadata={"source": str(path)}))

    return docs


def chunk_docs(docs: list[Document]) -> list:
    print(
        f"Chunking {len(docs)} documents with chunk size {CHUNK_SIZE} and overlap {CHUNK_OVERLAP}")

    text_splitter = RecursiveCharacterTextSplitter.from_language(
        language="python",
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP)

    return text_splitter.split_documents(docs)


def build_vector_store(chunks: list) -> Chroma:
    print(f"Building vector store with {len(chunks)} chunks...")

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2")

    return Chroma.from_documents(chunks, embeddings)


def build_agent(vector_store: Chroma) -> create_agent:
    search_codebase = create_retriever_tool(
        vector_store.as_retriever(search_kwargs={"k": 4}),
        name="search_codebase",
        description="Search the codebase for relevant functions, classes, or logic.")

    llm_instance = ChatOpenAI(
        model="llama-3.3-70b-versatile", temperature=0)

    system_message = SystemMessage(
        content="You are a senior engineer. Always use search_codebase before answering. Reference specific file and function names. If not found say 'I could not find that in the codebase'. Never write XML-style function calls manually.`")

    # limiting tool or model calls
    middleware = [
        ModelCallLimitMiddleware(run_limit=5, exit_behavior='end'),

        ToolCallLimitMiddleware(
            tool_name='search_codebase', run_limit=2, exit_behavior='continue')
    ]

    return create_agent(
        llm_instance,
        tools=[search_codebase],
        system_prompt=system_message,
        middleware=middleware)


if __name__ == "__main__":
    # Load and chunk documents (resolve path relative to this script, not CWD)
    datasources_path = Path(__file__).parent.parent / "sample_project"
    print(datasources_path)
    
    docs = load_all_docs(datasources_path)
    chunks = chunk_docs(docs)

    print(type(chunks), len(chunks))

    
    # Build vector store and agent
    vector_store = build_vector_store(chunks)
    print(vector_store)
    agent = build_agent(vector_store)
    print(agent)

    

    while True:
        query = input("Ask a question about the codebase: ")

        if query.lower() in ["exit", "quit"]:
            break

        for chunk in agent.stream(
            {"messages": [HumanMessage(content=query)]},
            stream_mode=["values"],
            version="v2",
        ):
            last_message = chunk['data']['messages'][-1].content

        print("\nAgent response:")
        print(last_message)
        