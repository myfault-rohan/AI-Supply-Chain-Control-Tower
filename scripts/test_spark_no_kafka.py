# DEVELOPMENT UTILITY — not part of main application
from pyspark.sql import SparkSession
import os

def main():
    print("Testing Spark session creation WITHOUT Kafka...")
    try:
        spark = SparkSession.builder \
            .appName("TestAppNoKafka") \
            .master("local[*]") \
            .getOrCreate()
        print("Spark session created successfully!")
        print(f"Spark Version: {spark.version}")
        spark.stop()
    except Exception as e:
        print(f"Failed to create Spark session: {e}")

if __name__ == "__main__":
    main()
