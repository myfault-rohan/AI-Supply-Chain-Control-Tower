import os
import json
import pandas as pd
from anthropic import Anthropic
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import DATASET_DIR
from dotenv import load_dotenv

load_dotenv()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

def ask_supply_chain_question(question: str) -> str:
    if not ANTHROPIC_API_KEY:
        return "Anthropic API key is not configured. Please set ANTHROPIC_API_KEY in .env."
    
    processed_dir = os.path.join(DATASET_DIR, "processed files")
    context_data = {}
    for fname in ["supply_chain_health.csv", "reorder_recommendations.csv", "supplier_performance.csv", "cost_analysis.csv"]:
        fpath = os.path.join(processed_dir, fname)
        if os.path.exists(fpath):
            try:
                df = pd.read_csv(fpath)
                context_data[fname.replace('.csv', '')] = df.to_dict(orient="records")
            except Exception:
                pass

    context_json = json.dumps(context_data, default=str)[:80000] # safety limit

    system_prompt = f"""You are an expert supply chain analyst.
Here is live supply chain data: {context_json}.
Answer with specific product IDs, numbers, and actionable recommendations."""

    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1000,
            system=system_prompt,
            messages=[{"role": "user", "content": question}]
        )
        return response.content[0].text
    except Exception as e:
        return f"Error contacting AI: {e}"
