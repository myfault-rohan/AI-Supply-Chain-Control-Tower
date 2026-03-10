from pyspark.sql import SparkSession
import os

def main():
    print("Testing MINIMAL Structured Streaming (Rate Source)...")
    
    # Windows Workaround
    # Use forward slashes to avoid escape character issues in Spark/Hadoop
    hadoop_home = os.path.join(os.getcwd(), 'tmp', 'hadoop').replace('\\', '/')
    os.environ['HADOOP_HOME'] = hadoop_home
    os.environ['PATH'] = os.path.join(hadoop_home, 'bin').replace('\\', '/') + os.pathsep + os.environ.get('PATH', '')
    os.environ['HADOOP_OPTS'] = f"-Dhadoop.native.lib=false -Dhadoop.home.dir={hadoop_home}"
    
    spark = SparkSession.builder \
        .appName("TestStreamingNoKafka") \
        .config("spark.driver.extraJavaOptions", f"-Djava.library.path={hadoop_home}/bin -Dhadoop.native.lib=false -Dhadoop.home.dir={hadoop_home}") \
        .config("spark.executor.extraJavaOptions", f"-Djava.library.path={hadoop_home}/bin -Dhadoop.native.lib=false -Dhadoop.home.dir={hadoop_home}") \
        .config("spark.hadoop.fs.file.impl", "org.apache.hadoop.fs.RawLocalFileSystem") \
        .config("spark.hadoop.fs.AbstractFileSystem.file.impl", "org.apache.hadoop.fs.local.RawLocalFs") \
        .config("spark.hadoop.hadoop.native.lib", "false") \
        .config("spark.driver.host", "127.0.0.1") \
        .master("local[*]") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("ERROR")
    
    try:
        # Rate source doesn't require Kafka jars
        stream = spark.readStream \
            .format("rate") \
            .option("rowsPerSecond", 1) \
            .load()
            
        # Console sink
        query = stream.writeStream \
            .outputMode("append") \
            .format("console") \
            .start()
            
        print("Streaming query started successfully!")
        query.processAllAvailable()
        query.stop()
        print("Streaming test completed successfully!")
        
    except Exception as e:
        print(f"Streaming failed: {e}")
    finally:
        spark.stop()

if __name__ == "__main__":
    main()
