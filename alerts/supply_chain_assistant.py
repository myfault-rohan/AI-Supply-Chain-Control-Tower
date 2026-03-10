"""
AI Supply Chain Assistant
Provides text-based answers to supply chain queries using the reorder recommendations dataset.
"""

import pandas as pd
import os

class SupplyChainAssistant:
    def __init__(self, filepath):
        """Initialize with the latest reorder recommendations data"""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Data file not found: {filepath}. Please run the risk engine first.")
        self.df = pd.read_csv(filepath)

    def get_stockout_soon(self):
        """Answer: Which products will stock out soon?"""
        risk_df = self.df[self.df['stockout_risk'] == True]
        if risk_df.empty:
            return "No products are at immediate risk of stockout based on the current lead times."
        
        responses = []
        for _, row in risk_df.iterrows():
            responses.append(f"Product {row['product_id']} will stock out in {row['days_until_stockout']:.0f} days. Recommended reorder quantity is {row['reorder_quantity']:.0f} units.")
        return "\n".join(responses)

    def get_highest_demand(self):
        """Answer: Which product has highest predicted demand?"""
        if self.df.empty:
            return "I don't have enough data to determine demand trends yet."
        
        max_row = self.df.loc[self.df['predicted_demand'].idxmax()]
        return f"Product {max_row['product_id']} has the highest predicted demand, currently estimated at {max_row['predicted_demand']:.2f} units per day."

    def get_reorder_today(self):
        """Answer: What should we reorder today?"""
        reorder_df = self.df[self.df['reorder_quantity'] > 0]
        if reorder_df.empty:
            return "Good news! No reorders are required today. All stock levels are healthy."
        
        responses = ["Here are today's reorder recommendations:"]
        for _, row in reorder_df.iterrows():
            responses.append(f"- Product {row['product_id']}: Reorder {row['reorder_quantity']:.0f} units. ({row['alert_message']})")
        return "\n".join(responses)

    def ask(self, question):
        """Main interface for natural language style queries"""
        q = str(question).lower()
        
        if "stock out" in q or "stockout" in q:
            return self.get_stockout_soon()
        elif "highest" in q and "demand" in q:
            return self.get_highest_demand()
        elif "reorder" in q or "today" in q:
            return self.get_reorder_today()
        else:
            return (
                "I'm sorry, I didn't quite catch that. I can currently help you with:\n"
                "1. Identifying products that will stock out soon.\n"
                "2. Finding products with the highest demand.\n"
                "3. Recommending what to reorder today."
            )

def main():
    FILEPATH = 'dataset/reorder_recommendations.csv'
    
    print("=" * 60)
    print("🤖 AI SUPPLY CHAIN ASSISTANT")
    print("=" * 60)
    
    try:
        assistant = SupplyChainAssistant(FILEPATH)
        print("Ready to assist! (Type 'exit' to quit)\n")
        
        while True:
            try:
                user_input = input("How can I help you today? ")
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    print("Goodbye! Stay efficient.")
                    break
                
                if not user_input.strip():
                    continue
                    
                response = assistant.ask(user_input)
                print(f"\nAssistant: {response}\n")
                
            except EOFError:
                break
                
    except Exception as e:
        print(f"Error initializing assistant: {e}")

if __name__ == "__main__":
    main()
