import pandas as pd
import os

def analyze_supplier_performance():
    """Analyzes supplier performance based on shipment data."""
    input_file = "dataset/shipments.csv"
    output_file = "dataset/supplier_performance.csv"

    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    # 1. Load dataset
    df = pd.read_csv(input_file)

    # 2. Convert delivery columns to datetime
    df['expected_delivery'] = pd.to_datetime(df['expected_delivery'])
    df['actual_delivery'] = pd.to_datetime(df['actual_delivery'])

    # Filter for shipments that have actual delivery data
    df_delivered = df.dropna(subset=['actual_delivery']).copy()

    # 3. Calculate delay_days
    df_delivered['delay_days'] = (df_delivered['actual_delivery'] - df_delivered['expected_delivery']).dt.days

    # 4. Calculate metrics per supplier
    supplier_metrics = df_delivered.groupby('supplier_id').agg(
        average_delay=('delay_days', 'mean'),
        total_shipments=('shipment_id', 'count'),
        on_time_shipments=('delay_days', lambda x: (x <= 0).sum())
    ).reset_index()

    # 5. Calculate reliability_score
    supplier_metrics['reliability_score'] = (supplier_metrics['on_time_shipments'] / supplier_metrics['total_shipments']) * 100
    supplier_metrics['delay_rate'] = 100 - supplier_metrics['reliability_score']

    # 6. Classify supplier status
    def classify_status(score):
        if score > 85:
            return "GOOD"
        elif 60 <= score <= 85:
            return "WARNING"
        else:
            return "CRITICAL"

    supplier_metrics['supplier_status'] = supplier_metrics['reliability_score'].apply(classify_status)

    # 7. Save results
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    supplier_metrics.to_csv(output_file, index=False)
    
    print(f"Supplier performance analysis saved to {output_file}")
    print("\nSample Results:")
    print(supplier_metrics.head())

if __name__ == "__main__":
    analyze_supplier_performance()
