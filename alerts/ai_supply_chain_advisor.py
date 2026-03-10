import pandas as pd

def load_data():
    try:
        df = pd.read_csv("dataset/supply_chain_health.csv")
        return df
    except:
        return None


def ask_supply_chain_question(question):

    df = load_data()

    if df is None:
        return "No supply chain data available."

    question = question.lower()

    if "stock out" in question or "stockout" in question:

        critical = df[df["health_status"] == "CRITICAL"]

        if critical.empty:
            return "No products are at immediate stockout risk."

        result = "Products at risk of stockout:\n"

        for _, row in critical.iterrows():
            result += f"Product {row['product_id']} will stock out in {row['days_until_stockout']} days.\n"

        return result


    elif "reorder" in question:

        risky = df[df["days_until_stockout"] < 5]

        if risky.empty:
            return "No urgent reorders required."

        result = "Recommended reorder actions:\n"

        for _, row in risky.iterrows():
            result += f"Reorder product {row['product_id']} immediately.\n"

        return result


    elif "inventory" in question:

        avg_stock = df["current_stock"].mean()

        return f"The average inventory level across products is {int(avg_stock)} units."

    else:
        return "I can answer questions about stockouts, inventory levels, and reorder recommendations."
