"""
PySpark Data Processing Pipeline for Supply Chain System
Processes inventory, sales, and shipment data with cleaning and analytics.
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, when, avg, stddev, to_date, datediff, lag, sum as spark_sum, 
    monotonically_increasing_id, row_number, coalesce, lit
)
from pyspark.sql.window import Window
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType, DateType
import os

# Configuration
INPUT_DIR = 'dataset/'
OUTPUT_FILE = 'dataset/processed_supply_chain.csv'

# Input files
INVENTORY_FILE = os.path.join(INPUT_DIR, 'stream_inventory.csv')
SALES_FILE = os.path.join(INPUT_DIR, 'stream_sales.csv')
SHIPMENTS_FILE = os.path.join(INPUT_DIR, 'stream_shipments.csv')


def create_spark_session():
    """Create and return a Spark session"""
    return SparkSession.builder \
        .appName("SupplyChainProcessing") \
        .master("local[*]") \
        .config("spark.driver.memory", "4g") \
        .getOrCreate()


def load_inventory_data(spark):
    """Load inventory data from CSV"""
    print("Loading inventory data...")
    
    # Define schema for inventory
    schema = StructType([
        StructField("product_id", StringType(), True),
        StructField("warehouse_id", StringType(), True),
        StructField("current_stock", DoubleType(), True),
        StructField("safety_stock", DoubleType(), True),
        StructField("reorder_point", DoubleType(), True),
        StructField("timestamp", StringType(), True)
    ])
    
    df = spark.read.csv(INVENTORY_FILE, header=True, schema=schema)
    print(f"Loaded {df.count()} inventory records")
    return df


def load_sales_data(spark):
    """Load sales data from CSV"""
    print("Loading sales data...")
    
    # Define schema for sales
    schema = StructType([
        StructField("product_id", StringType(), True),
        StructField("date", StringType(), True),
        StructField("daily_sales", DoubleType(), True),
        StructField("region", StringType(), True),
        StructField("timestamp", StringType(), True)
    ])
    
    df = spark.read.csv(SALES_FILE, header=True, schema=schema)
    print(f"Loaded {df.count()} sales records")
    return df


def load_shipments_data(spark):
    """Load shipments data from CSV"""
    print("Loading shipments data...")
    
    # Define schema for shipments
    schema = StructType([
        StructField("shipment_id", StringType(), True),
        StructField("supplier_id", StringType(), True),
        StructField("product_id", StringType(), True),
        StructField("shipment_date", StringType(), True),
        StructField("expected_delivery", StringType(), True),
        StructField("actual_delivery", StringType(), True),
        StructField("status", StringType(), True),
        StructField("timestamp", StringType(), True)
    ])
    
    df = spark.read.csv(SHIPMENTS_FILE, header=True, schema=schema)
    print(f"Loaded {df.count()} shipment records")
    return df


def clean_missing_values(inventory_df, sales_df, shipments_df):
    """Clean missing values in all datasets"""
    print("\n--- Cleaning Missing Values ---")
    
    # Clean inventory data
    inventory_clean = inventory_df \
        .filter(col("product_id").isNotNull()) \
        .fillna({
            "current_stock": 0,
            "safety_stock": 0,
            "reorder_point": 0,
            "warehouse_id": "UNKNOWN"
        })
    
    print(f"Inventory: {inventory_df.count()} -> {inventory_clean.count()} records after cleaning")
    
    # Clean sales data
    sales_clean = sales_df \
        .filter(col("product_id").isNotNull()) \
        .fillna({
            "daily_sales": 0,
            "region": "UNKNOWN",
            "date": "1970-01-01"
        })
    
    print(f"Sales: {sales_df.count()} -> {sales_clean.count()} records after cleaning")
    
    # Clean shipments data
    shipments_clean = shipments_df \
        .filter(col("product_id").isNotNull()) \
        .fillna({
            "supplier_id": "UNKNOWN",
            "shipment_date": "1970-01-01",
            "expected_delivery": "1970-01-01",
            "actual_delivery": "1970-01-01",
            "status": "UNKNOWN"
        })
    
    print(f"Shipments: {shipments_df.count()} -> {shipments_clean.count()} records after cleaning")
    
    return inventory_clean, sales_clean, shipments_clean


def calculate_inventory_days(inventory_df, sales_df):
    """Calculate inventory_days = current_stock / average_daily_sales"""
    print("\n--- Calculating Inventory Days ---")
    
    # Calculate average daily sales per product
    avg_sales = sales_df.groupBy("product_id").agg(
        avg("daily_sales").alias("avg_daily_sales")
    )
    
    # Join inventory with average sales
    inventory_with_avg = inventory_df.join(
        avg_sales, 
        on="product_id", 
        how="left"
    )
    
    # Fill missing average sales with 1 to avoid division by zero
    inventory_with_avg = inventory_with_avg.withColumn(
        "avg_daily_sales", 
        coalesce(col("avg_daily_sales"), lit(1.0))
    )
    
    # Calculate inventory days
    inventory_with_days = inventory_with_avg.withColumn(
        "inventory_days",
        when(col("avg_daily_sales") > 0, 
             col("current_stock") / col("avg_daily_sales"))
        .otherwise(lit(None))
    )
    
    print(f"Calculated inventory_days for {inventory_with_days.count()} records")
    
    return inventory_with_days.drop("avg_daily_sales")


def detect_supplier_delivery_delay(shipments_df):
    """Detect supplier delivery delay: delay_days = actual_delivery - expected_delivery"""
    print("\n--- Detecting Supplier Delivery Delays ---")
    
    # Convert date strings to date type
    shipments_with_dates = shipments_df \
        .withColumn("expected_delivery_date", to_date(col("expected_delivery"), "yyyy-MM-dd")) \
        .withColumn("actual_delivery_date", to_date(col("actual_delivery"), "yyyy-MM-dd"))
    
    # Calculate delay in days (positive = delayed, negative = early)
    shipments_with_delay = shipments_with_dates.withColumn(
        "delay_days",
        when(col("actual_delivery_date").isNotNull() & col("expected_delivery_date").isNotNull(),
             datediff(col("actual_delivery_date"), col("expected_delivery_date")))
        .otherwise(lit(0))
    )
    
    # Mark as delayed if delay_days > 0
    shipments_with_delay = shipments_with_delay.withColumn(
        "is_delayed",
        when(col("delay_days") > 0, lit(True)).otherwise(False)
    )
    
    delayed_count = shipments_with_delay.filter(col("is_delayed") == True).count()
    print(f"Detected {delayed_count} delayed shipments")
    
    return shipments_with_delay


def detect_demand_spikes(sales_df):
    """Detect demand spikes: demand_spike = daily_sales > 1.5 * rolling_average"""
    print("\n--- Detecting Demand Spikes ---")
    
    # Window specification for rolling average (last 7 days)
    window_spec = Window.partitionBy("product_id", "region") \
        .orderBy("date") \
        .rowsBetween(-6, 0)  # 7-day rolling window including current
    
    # Add rolling average
    sales_with_rolling = sales_df.withColumn(
        "rolling_avg_sales",
        avg("daily_sales").over(window_spec)
    )
    
    # Fill missing rolling averages with the daily sales value
    sales_with_rolling = sales_with_rolling.withColumn(
        "rolling_avg_sales",
        coalesce(col("rolling_avg_sales"), col("daily_sales"))
    )
    
    # Detect demand spikes (daily_sales > 1.5 * rolling_average)
    sales_with_spike = sales_with_rolling.withColumn(
        "demand_spike",
        when((col("rolling_avg_sales").isNotNull()) & (col("daily_sales") > 1.5 * col("rolling_avg_sales")), 
             lit(True))
        .otherwise(lit(False))
    )
    
    spike_count = sales_with_spike.filter(col("demand_spike") == True).count()
    print(f"Detected {spike_count} demand spikes")
    
    return sales_with_spike


def join_datasets(inventory_df, sales_df, shipments_df):
    """Join all datasets based on product_id"""
    print("\n--- Joining Datasets ---")
    
    # Aggregate sales data by product_id
    sales_agg = sales_df.groupBy("product_id").agg(
        avg("daily_sales").alias("avg_daily_sales"),
        spark_sum("daily_sales").alias("total_daily_sales"),
        stddev("daily_sales").alias("stddev_daily_sales"),
        spark_sum(when(col("demand_spike") == True, 1).otherwise(0)).alias("total_spikes")
    )
    
    # Aggregate shipments data by product_id
    shipments_agg = shipments_df.groupBy("product_id").agg(
        spark_sum(when(col("is_delayed") == True, 1).otherwise(0)).alias("total_delays"),
        avg("delay_days").alias("avg_delay_days")
    )
    
    # Join inventory with sales
    joined_df = inventory_df.join(
        sales_agg,
        on="product_id",
        how="left"
    )
    
    # Join with shipments
    joined_df = joined_df.join(
        shipments_agg,
        on="product_id",
        how="left"
    )
    
    # Fill missing values with defaults
    joined_df = joined_df.fillna({
        "avg_daily_sales": 0.0,
        "total_daily_sales": 0.0,
        "stddev_daily_sales": 0.0,
        "total_spikes": 0,
        "total_delays": 0,
        "avg_delay_days": 0.0,
        "current_stock": 0.0,
        "safety_stock": 0.0,
        "reorder_point": 0.0
    })
    
    print(f"Joined dataset has {joined_df.count()} records")
    
    return joined_df


def write_output(df, output_path):
    """Write processed data to CSV using Pandas to avoid Hadoop dependency on Windows"""
    print(f"\n--- Writing Output to {output_path} ---")
    
    try:
        # Convert Spark DataFrame to Pandas
        pandas_df = df.toPandas()
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Write to CSV
        pandas_df.to_csv(output_path, index=False)
        print(f"Output written to {output_path}")
    except Exception as e:
        print(f"Error writing output with Pandas: {e}")
        # Fallback to spark write if pandas fails for some reason
        print("Attempting fallback to Spark native write...")
        df.coalesce(1).write.mode("overwrite").option("header", "true").csv(output_path + "_spark")


def main():
    """Main processing pipeline"""
    print("=" * 60)
    print("PySpark Supply Chain Data Processing Pipeline")
    print("=" * 60)
    
    # Create Spark session
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    
    try:
        # Step 1: Load data
        print("\n[Step 1] Loading data from CSV files...")
        inventory_df = load_inventory_data(spark)
        sales_df = load_sales_data(spark)
        shipments_df = load_shipments_data(spark)
        
        # Step 2: Clean missing values
        print("\n[Step 2] Cleaning missing values...")
        inventory_clean, sales_clean, shipments_clean = clean_missing_values(
            inventory_df, sales_df, shipments_df
        )
        
        # Step 3: Calculate inventory days
        print("\n[Step 3] Calculating inventory days...")
        inventory_with_days = calculate_inventory_days(inventory_clean, sales_clean)
        
        # Step 4: Detect supplier delivery delays
        print("\n[Step 4] Detecting supplier delivery delays...")
        shipments_with_delay = detect_supplier_delivery_delay(shipments_clean)
        
        # Step 5: Detect demand spikes
        print("\n[Step 5] Detecting demand spikes...")
        sales_with_spike = detect_demand_spikes(sales_clean)
        
        # Step 6: Join datasets
        print("\n[Step 6] Joining datasets based on product_id...")
        joined_df = join_datasets(
            inventory_with_days, 
            sales_with_spike, 
            shipments_with_delay
        )
        
        # Add boolean flags if they don't exist (handle case where joins are empty)
        final_df = joined_df
        if "is_delayed" not in final_df.columns:
            final_df = final_df.withColumn("is_delayed", lit(False))
        if "demand_spike" not in final_df.columns:
            final_df = final_df.withColumn("demand_spike", lit(False))
        
        # Select final columns for output
        output_columns = [
            "product_id",
            "warehouse_id",
            "current_stock",
            "safety_stock",
            "reorder_point",
            "inventory_days",
            "avg_daily_sales",
            "total_daily_sales",
            "rolling_avg_sales",
            "demand_spike",
            "shipment_id",
            "supplier_id",
            "expected_delivery",
            "actual_delivery",
            "delay_days",
            "is_delayed",
            "total_delays",
            "avg_delay_days",
            "timestamp"
        ]
        
        # Select only columns that exist
        final_columns = [col for col in output_columns if col in final_df.columns]
        final_df = final_df.select(final_columns)
        
        # Show sample output
        print("\n--- Sample Output ---")
        final_df.show(10, truncate=False)
        
        # Step 7: Write output
        print("\n[Step 7] Writing processed data to CSV...")
        write_output(final_df, OUTPUT_FILE)
        
        # Print summary
        print("\n" + "=" * 60)
        print("PROCESSING SUMMARY")
        print("=" * 60)
        print(f"Total processed records: {final_df.count()}")
        print(f"Products with demand spikes: {final_df.filter(col('demand_spike') == True).count()}")
        print(f"Products with delivery delays: {final_df.filter(col('is_delayed') == True).count()}")
        print(f"Output file: {OUTPUT_FILE}")
        print("=" * 60)
        print("Pipeline completed successfully!")
        
    except Exception as e:
        print(f"Error during processing: {e}")
        raise
    finally:
        spark.stop()


if __name__ == "__main__":
    main()

