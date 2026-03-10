# Start FastAPI
Start-Process powershell -ArgumentList "uvicorn backend.api_server:app --reload"

# Start Dashboard
Start-Process powershell -ArgumentList "streamlit run dashboard/dashboard_app.py"

# Start Spark Streaming
Start-Process powershell -ArgumentList "python spark_processing\spark_streaming_processor.py"

# Start Kafka Producer
Start-Process powershell -ArgumentList "python stream_pipeline\kafka_producer.py"
