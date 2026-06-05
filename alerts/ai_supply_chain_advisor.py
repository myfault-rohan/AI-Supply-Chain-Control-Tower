import os
import sys
import polars as pl
from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import DATASET_DIR

load_dotenv()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# -------------------------------------------------------------------------
# Lazy imports for heavy RAG dependencies — prevents dashboard crash when
# llama-index / chromadb / anthropic are not installed
# -------------------------------------------------------------------------
_RAG_AVAILABLE = False
_rag_index = None

try:
    import chromadb
    from llama_index.core import VectorStoreIndex, Document, StorageContext, Settings
    from llama_index.vector_stores.chroma import ChromaVectorStore
    from llama_index.llms.anthropic import Anthropic
    _RAG_AVAILABLE = True
except (ImportError, ValueError, OSError) as e:
    _RAG_AVAILABLE = False
    pass  # RAG will be disabled gracefully

_PYDANTIC_AI_AVAILABLE = False
supply_chain_agent = None

try:
    import pydantic_ai
    from pydantic import BaseModel, Field
    from typing import List, Optional

    class SupplyChainAdvice(BaseModel):
        summary: str = Field(description="A concise summary of the answer to the user's question.")
        action_items: List[str] = Field(description="List of recommended actions to take.")
        risk_level: str = Field(description="The risk level associated with the current situation (LOW, MEDIUM, HIGH, CRITICAL).")
        affected_products: Optional[List[str]] = Field(description="List of product IDs affected, if any.")

    supply_chain_agent = pydantic_ai.Agent(
        'anthropic:claude-3-haiku-20240307',
        result_type=SupplyChainAdvice,
        system_prompt=(
            "You are an elite AI Supply Chain Advisor. You analyze supply chain data and provide actionable advice. "
            "Always respond with structured data containing a summary, action items, risk level, and affected products."
        )
    )
    _PYDANTIC_AI_AVAILABLE = True
except ImportError:
    pass  # PydanticAI will be disabled gracefully


def get_or_build_rag_index():
    global _rag_index
    if not _RAG_AVAILABLE:
        return None
    if _rag_index is not None:
        return _rag_index

    # Configure LlamaIndex to use Anthropic
    Settings.llm = Anthropic(model="claude-3-haiku-20240307", api_key=ANTHROPIC_API_KEY)

    # Initialize ChromaDB Vector Store
    chroma_db_path = os.path.join(DATASET_DIR, "chroma_db")
    os.makedirs(chroma_db_path, exist_ok=True)
    chroma_client = chromadb.PersistentClient(path=chroma_db_path)
    chroma_collection = chroma_client.get_or_create_collection("supply_chain_knowledge")

    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    if chroma_collection.count() > 0:
        _rag_index = VectorStoreIndex.from_vector_store(vector_store, storage_context=storage_context)
        return _rag_index

    # Ingest CSV files using Polars
    processed_dir = os.path.join(DATASET_DIR, "processed files")
    documents = []

    files_to_ingest = [
        "demand_predictions.csv",
        "prophet_predictions.csv",
        "supply_chain_health.csv"
    ]

    for fname in files_to_ingest:
        fpath = os.path.join(processed_dir, fname)
        if os.path.exists(fpath):
            try:
                df = pl.read_csv(fpath)
                records = df.to_dicts()
                text_content = f"Source Document: {fname}\n\n"
                for row in records[:1000]:
                    text_content += str(row) + "\n"
                documents.append(Document(text=text_content, metadata={"source": fname}))
            except Exception as e:
                print(f"Polars/RAG Error loading {fname}: {e}")

    if not documents:
        documents.append(Document(
            text="No supply chain data available yet. Please run the ML pipelines first.",
            metadata={"source": "system"}
        ))

    _rag_index = VectorStoreIndex.from_documents(documents, storage_context=storage_context)
    return _rag_index


def ask_supply_chain_question(question: str) -> str:
    """
    Query the supply chain RAG pipeline and return a structured JSON response via PydanticAI.
    Falls back to a helpful message if API key or dependencies are missing.
    """
    if not ANTHROPIC_API_KEY:
        return (
            '{"error": "Anthropic API key is not configured. '
            'Please add ANTHROPIC_API_KEY=your-key to your .env file to enable the AI Advisor."}'
        )

    if not _RAG_AVAILABLE:
        return (
            '{"error": "RAG dependencies not installed. '
            'Run: pip install llama-index chromadb llama-index-llms-anthropic llama-index-vector-stores-chroma"}'
        )

    if not _PYDANTIC_AI_AVAILABLE:
        return '{"error": "pydantic-ai not installed. Run: pip install pydantic-ai"}'

    try:
        index = get_or_build_rag_index()
        if index is None:
            return '{"error": "Could not build RAG index. Check DATASET_DIR and dependencies."}'

        query_engine = index.as_query_engine(similarity_top_k=3)
        rag_context = query_engine.query(question)

        prompt = f"User Question: {question}\n\nContext from Database:\n{rag_context}"
        result = supply_chain_agent.run_sync(prompt)
        return result.data.model_dump_json(indent=2)

    except Exception as e:
        return f'{{"error": "Error contacting AI Advisor: {str(e)}"}}'
