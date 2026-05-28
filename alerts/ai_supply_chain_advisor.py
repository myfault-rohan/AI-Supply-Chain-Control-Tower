import os
import sys
import polars as pl
from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import DATASET_DIR

# -------------------------------------------------------------------------
# LlamaIndex & ChromaDB imports
# -------------------------------------------------------------------------
import chromadb
from llama_index.core import VectorStoreIndex, Document, StorageContext, Settings
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.llms.anthropic import Anthropic

load_dotenv()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Global cache for the RAG index
_rag_index = None

def get_or_build_rag_index():
    global _rag_index
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
    
    # If the collection already has documents, just load the index
    if chroma_collection.count() > 0:
        _rag_index = VectorStoreIndex.from_vector_store(vector_store, storage_context=storage_context)
        return _rag_index
        
    # Otherwise, ingest CSV files using Polars
    processed_dir = os.path.join(DATASET_DIR, "processed files")
    documents = []
    
    # In a real app we would read all reports, here we pick the key analytical outputs
    files_to_ingest = [
        "demand_predictions.csv", 
        "prophet_predictions.csv", 
        "supply_chain_health.csv"
    ]
    
    for fname in files_to_ingest:
        fpath = os.path.join(processed_dir, fname)
        if os.path.exists(fpath):
            try:
                # Use Polars for blazing fast data loading (replaces Pandas)
                df = pl.read_csv(fpath)
                
                # Convert Polars DataFrame to a text representation for RAG
                records = df.to_dicts()
                text_content = f"Source Document: {fname}\n\n"
                
                # To avoid giant documents, we could chunk them, but for this portfolio 
                # we'll create one Document per file, and LlamaIndex handles chunking internally.
                for row in records[:1000]:  # Limit to 1000 rows per file for prompt safety
                    text_content += str(row) + "\n"
                
                documents.append(Document(text=text_content, metadata={"source": fname}))
            except Exception as e:
                print(f"Polars/RAG Error loading {fname}: {e}")
                
    if not documents:
        # Fallback if no files exist yet
        documents.append(Document(text="No supply chain data available yet. Please run the ML pipelines first.", metadata={"source": "system"}))
        
    # Build and persist the index to ChromaDB
    _rag_index = VectorStoreIndex.from_documents(documents, storage_context=storage_context)
    return _rag_index

import pydantic_ai
from pydantic import BaseModel, Field
from typing import List, Optional

class SupplyChainAdvice(BaseModel):
    summary: str = Field(description="A concise summary of the answer to the user's question.")
    action_items: List[str] = Field(description="List of recommended actions to take.")
    risk_level: str = Field(description="The risk level associated with the current situation (LOW, MEDIUM, HIGH, CRITICAL).")
    affected_products: Optional[List[str]] = Field(description="List of product IDs affected, if any.")

# Create the PydanticAI Agent
supply_chain_agent = pydantic_ai.Agent(
    'anthropic:claude-3-haiku-20240307',
    result_type=SupplyChainAdvice,
    system_prompt=(
        "You are an elite AI Supply Chain Advisor. You analyze supply chain data and provide actionable advice. "
        "Always respond with structured data containing a summary, action items, risk level, and affected products."
    )
)

def ask_supply_chain_question(question: str) -> str:
    """
    Query the supply chain RAG pipeline and return a structured JSON response via PydanticAI.
    """
    if not ANTHROPIC_API_KEY:
        return '{"error": "Anthropic API key is not configured. Please set ANTHROPIC_API_KEY in .env."}'
        
    try:
        # First, retrieve relevant context using LlamaIndex RAG
        index = get_or_build_rag_index()
        query_engine = index.as_query_engine(similarity_top_k=3)
        rag_context = query_engine.query(question)
        
        # Then, use PydanticAI to structure the response robustly
        prompt = f"User Question: {question}\n\nContext from Database:\n{rag_context}"
        
        # We pass the api key to the model settings implicitly via env vars, 
        # but pydantic_ai reads ANTHROPIC_API_KEY automatically.
        result = supply_chain_agent.run_sync(prompt)
        
        # Return the structured JSON
        return result.data.model_dump_json(indent=2)
    except Exception as e:
        return f'{{"error": "Error contacting AI Advisor (PydanticAI Pipeline): {e}"}}'
