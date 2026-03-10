import os
import sys
import logging

# Set HADOOP_HOME environment variable for Windows (must be absolute path)
# This is necessary for Spark to work correctly on Windows.
_project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ['HADOOP_HOME'] = os.path.join(_project_dir, 'tmp', 'hadoop')
# Ensure winutils.exe is on the PATH
os.environ['PATH'] = os.path.join(os.environ['HADOOP_HOME'], 'bin') + os.pathsep + os.environ.get('PATH', '')

from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StructField, IntegerType, StringType

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def process_inventory_stream():
    """
    Processes real-time inventory updates from Kafka using PySpark Structured Streaming.
    """
    try:
        # 1. Create SparkSession
        # Using PySpark 3.5.x with Scala 2.12 Kafka connector for compatibility
        spark = SparkSession.builder \
            .appName("SupplyChainStreamingProcessor") \
            .master("local[*]") \
            .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.8") \
            .config("spark.sql.streaming.checkpointLocation", "dataset/stream_checkpoint") \
            .getOrCreate()

        # Set log level to WARN to reduce verbosity
        spark.sparkContext.setLogLevel("WARN")
        logging.info("SparkSession created successfully.")

        # 2. Read streaming data from Kafka
        kafka_stream_df = spark.readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", "localhost:9092") \
            .option("subscribe", "inventory_updates") \
            .option("startingOffsets", "latest") \
            .load()
        
        logging.info("Successfully connected to Kafka topic 'inventory_updates'.")

        # 3. Define the schema for the Kafka JSON messages matching inventory.csv
        schema = StructType([
            StructField("product_id", StringType(), True),
            StructField("product_name", StringType(), True),
            StructField("warehouse_id", StringType(), True),
            StructField("current_stock", IntegerType(), True),
            StructField("safety_stock", IntegerType(), True),
            StructField("reorder_point", IntegerType(), True),
            StructField("daily_demand", IntegerType(), True),
            StructField("timestamp", StringType(), True)
        ])

        # 4. Parse the JSON message from Kafka
        # Convert the 'value' column from binary to string
        json_df = kafka_stream_df.select(col("value").cast("string"))

        # Parse the JSON string into a struct
        parsed_df = json_df.withColumn("data", from_json(col("value"), schema)) \
                           .select("data.*")

        # 5. Perform the transformation: calculate inventory_days
        # Avoid division by zero by checking if daily_demand is > 0
        processed_df = parsed_df.withColumn(
            "inventory_days",
            col("current_stock") / col("daily_demand")
        )
        
        logging.info("Data transformation logic defined.")

        # 6. Write the streaming results to a CSV file
        # The output will be written to a directory, not a single file.
        query = processed_df.writeStream \
            .outputMode("append") \
            .format("csv") \
            .option("path", "dataset/live_supply_chain") \
            .option("header", "true") \
            .start()

        logging.info("Streaming query started. Writing to 'dataset/live_supply_chain'.")
        logging.info("Waiting for termination...")

        # 7. The script should run continuously until stopped
        query.awaitTermination()

    except Exception as e:
        logging.error(f"An error occurred in the Spark streaming process: {e}")
        # In a production scenario, you might want to add more robust error handling
        # or cleanup logic here.

if __name__ == "__main__":
    process_inventory_stream()
