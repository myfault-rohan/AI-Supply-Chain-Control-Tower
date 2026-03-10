import os
import sys

# Set HADOOP_HOME environment variable for Windows (must be absolute path)
_project_dir = os.path.dirname(os.path.abspath(__file__))
os.environ['HADOOP_HOME'] = os.path.join(_project_dir, 'tmp', 'hadoop')
os.environ['PATH'] = os.path.join(os.environ['HADOOP_HOME'], 'bin') + os.pathsep + os.environ.get('PATH', '')

from pyspark.sql import SparkSession

def main():
    print("Testing Spark session creation...")
    try:
        spark = SparkSession.builder \
            .appName("TestApp") \
            .master("local[*]") \
            .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.8") \
            .getOrCreate()
        print("Spark session created successfully!")
        print(f"Spark Version: {spark.version}")
        spark.stop()
    except Exception as e:
        print(f"Failed to create Spark session: {e}")

if __name__ == "__main__":
    main()
