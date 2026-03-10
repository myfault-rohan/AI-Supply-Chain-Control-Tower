"""
Kafka Consumer for Supply Chain Data Streams
Listens to inventory_updates, sales_updates, and shipment_updates topics
and appends data to local CSV files.
"""

import json
import os
import pandas as pd
from kafka import KafkaConsumer
from datetime import datetime

# Configuration
KAFKA_BOOTSTRAP_SERVERS = 'localhost:9092'
TOPICS = ['inventory_updates', 'sales_updates', 'shipment_updates']
CONSUMER_GROUP = 'supply_chain_consumer'

# Output file paths
OUTPUT_DIR = 'dataset/'
OUTPUT_FILES = {
    'inventory_updates': os.path.join(OUTPUT_DIR, 'stream_inventory.csv'),
    'sales_updates': os.path.join(OUTPUT_DIR, 'stream_sales.csv'),
    'shipment_updates': os.path.join(OUTPUT_DIR, 'stream_shipments.csv')
}

# CSV column headers matching the original datasets
CSV_HEADERS = {
    'inventory_updates': ['product_id', 'warehouse_id', 'current_stock', 'safety_stock', 'reorder_point', 'timestamp'],
    'sales_updates': ['product_id', 'date', 'daily_sales', 'region', 'timestamp'],
    'shipment_updates': ['shipment_id', 'supplier_id', 'product_id', 'shipment_date', 'expected_delivery', 'actual_delivery', 'status', 'timestamp']
}


def initialize_csv_files():
    """Initialize CSV files with headers if they don't exist"""
    for topic, filepath in OUTPUT_FILES.items():
        if not os.path.exists(filepath):
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            df = pd.DataFrame(columns=CSV_HEADERS[topic])
            df.to_csv(filepath, index=False)
            print(f"Initialized: {filepath}")


def append_to_csv(topic: str, data: dict):
    """Append JSON data to the corresponding CSV file"""
    filepath = OUTPUT_FILES.get(topic)
    if not filepath:
        print(f"Unknown topic: {topic}")
        return
    
    try:
        # Convert JSON to DataFrame and ensure correct column order/filter
        df_new = pd.DataFrame([data])
        
        # Only keep columns that are in CSV_HEADERS for this topic
        headers = CSV_HEADERS.get(topic)
        if headers:
            df_new = df_new[headers]
        
        # Append to CSV
        df_new.to_csv(filepath, mode='a', header=False, index=False)
        print(f"Appended data to {filepath}: {data}")
    except Exception as e:
        print(f"Error appending to {filepath}: {e}")


def create_consumer() -> KafkaConsumer:
    """Create and return a Kafka consumer instance"""
    return KafkaConsumer(
        *TOPICS,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=CONSUMER_GROUP,
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        consumer_timeout_ms=1000  # Timeout to allow periodic checks
    )


def consume_messages():
    """Main consumer loop - reads messages continuously"""
    print("Initializing Kafka consumer...")
    initialize_csv_files()
    
    print(f"Connecting to Kafka at {KAFKA_BOOTSTRAP_SERVERS}")
    print(f"Subscribing to topics: {TOPICS}")
    
    try:
        consumer = create_consumer()
        print("Consumer started. Waiting for messages...")
        
        message_count = 0
        while True:
            try:
                # Poll for messages
                messages = consumer.poll(timeout_ms=1000)
                
                for topic_partition, records in messages.items():
                    topic = topic_partition.topic
                    
                    for record in records:
                        message_count += 1
                        data = record.value
                        
                        # Add timestamp if not present
                        if 'timestamp' not in data:
                            data['timestamp'] = datetime.now().isoformat()
                        
                        # Append to CSV
                        append_to_csv(topic, data)
                        
                # Print progress every 100 messages
                if message_count % 100 == 0 and message_count > 0:
                    print(f"Processed {message_count} messages...")
                    
            except StopIteration:
                # Timeout reached, continue the loop
                continue
                
    except KeyboardInterrupt:
        print(f"\nConsumer stopped by user. Total messages processed: {message_count}")
    except Exception as e:
        print(f"Consumer error: {e}")
        raise


def consume_single_topic(topic: str, max_messages: int = None):
    """Alternative: Consume from a single topic (useful for testing)"""
    print(f"Consuming from topic: {topic}")
    initialize_csv_files()
    
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=CONSUMER_GROUP,
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        consumer_timeout_ms=1000
    )
    
    message_count = 0
    try:
        while True:
            try:
                messages = consumer.poll(timeout_ms=1000)
                
                for topic_partition, records in messages.items():
                    for record in records:
                        message_count += 1
                        data = record.value
                        
                        if 'timestamp' not in data:
                            data['timestamp'] = datetime.now().isoformat()
                        
                        append_to_csv(topic_partition.topic, data)
                        
                        if max_messages and message_count >= max_messages:
                            print(f"Reached max messages: {max_messages}")
                            return
                            
            except StopIteration:
                continue
                
    except KeyboardInterrupt:
        print(f"Stopped. Total messages: {message_count}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Kafka Consumer for Supply Chain Data')
    parser.add_argument('--topic', type=str, default=None, 
                        help='Specific topic to consume from (optional)')
    parser.add_argument('--max-messages', type=int, default=None,
                        help='Maximum messages to process (optional, for testing)')
    parser.add_argument('--bootstrap-servers', type=str, default=KAFKA_BOOTSTRAP_SERVERS,
                        help='Kafka bootstrap servers')
    
    args = parser.parse_args()
    
    if args.bootstrap_servers:
        KAFKA_BOOTSTRAP_SERVERS = args.bootstrap_servers
    
    if args.topic:
        consume_single_topic(args.topic, args.max_messages)
    else:
        consume_messages()

