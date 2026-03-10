"""
Kafka Producer for Supply Chain Inventory Updates
Reads inventory data from CSV and sends to Kafka topic as JSON messages.
"""

import json
import time
import pandas as pd
from kafka import KafkaProducer
from datetime import datetime

# Configuration
KAFKA_BOOTSTRAP_SERVERS = 'localhost:9092'
KAFKA_TOPIC = 'inventory_updates'
INPUT_FILE = 'dataset/inventory.csv'
MESSAGE_DELAY_SECONDS = 1


def create_producer() -> KafkaProducer:
    """Create and return a Kafka producer instance"""
    return KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        acks='all',  # Wait for all replicas
        retries=3,
        retry_backoff_ms=1000
    )


def read_inventory_data(filepath: str) -> pd.DataFrame:
    """Read inventory data from CSV file"""
    print(f"Reading inventory data from: {filepath}")
    df = pd.read_csv(filepath)
    print(f"Loaded {len(df)} inventory records")
    return df


def send_inventory_updates(producer: KafkaProducer, df: pd.DataFrame):
    """Send each inventory row as JSON to Kafka topic"""
    print(f"Sending messages to topic: {KAFKA_TOPIC}")
    print(f"Delay between messages: {MESSAGE_DELAY_SECONDS} second(s)")
    
    message_count = 0
    error_count = 0
    
    for index, row in df.iterrows():
        try:
            # Convert row to dictionary
            inventory_data = row.to_dict()
            
            # Add timestamp for when the message was sent
            inventory_data['timestamp'] = datetime.now().isoformat()
            
            # Send to Kafka
            future = producer.send(KAFKA_TOPIC, value=inventory_data)
            
            # Wait for send to complete (optional, ensures delivery)
            record_metadata = future.get(timeout=10)
            
            message_count += 1
            
            # Print progress every 10 messages
            if message_count % 10 == 0:
                print(f"Sent {message_count}/{len(df)} messages...")
            
            print(f"Sent: {inventory_data['product_id']} -> {inventory_data['warehouse_id']} "
                  f"(partition: {record_metadata.partition}, offset: {record_metadata.offset})")
            
            # Delay between messages
            time.sleep(MESSAGE_DELAY_SECONDS)
            
        except Exception as e:
            error_count += 1
            print(f"Error sending message {index}: {e}")
            continue
    
    return message_count, error_count


def main():
    """Main producer function"""
    print("=" * 60)
    print("Kafka Producer - Supply Chain Inventory Updates")
    print("=" * 60)
    
    # Read inventory data
    try:
        inventory_df = read_inventory_data(INPUT_FILE)
    except FileNotFoundError:
        print(f"Error: File not found: {INPUT_FILE}")
        return
    except Exception as e:
        print(f"Error reading file: {e}")
        return
    
    # Create Kafka producer
    print(f"Connecting to Kafka at: {KAFKA_BOOTSTRAP_SERVERS}")
    producer = create_producer()
    
    try:
        # Send inventory updates
        sent_count, error_count = send_inventory_updates(producer, inventory_df)
        
        # Flush any remaining messages
        producer.flush()
        
        print("\n" + "=" * 60)
        print("PRODUCTION SUMMARY")
        print("=" * 60)
        print(f"Total records:    {len(inventory_df)}")
        print(f"Messages sent:    {sent_count}")
        print(f"Errors:           {error_count}")
        print(f"Topic:            {KAFKA_TOPIC}")
        print(f"Bootstrap Server: {KAFKA_BOOTSTRAP_SERVERS}")
        print("=" * 60)
        print("Producer finished!")
        
    except KeyboardInterrupt:
        print("\nProducer stopped by user")
    finally:
        producer.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Kafka Producer for Inventory Updates')
    parser.add_argument('--file', type=str, default=INPUT_FILE,
                       help='Input CSV file path')
    parser.add_argument('--topic', type=str, default=KAFKA_TOPIC,
                       help='Kafka topic name')
    parser.add_argument('--delay', type=float, default=MESSAGE_DELAY_SECONDS,
                       help='Delay between messages in seconds')
    parser.add_argument('--bootstrap-servers', type=str, default=KAFKA_BOOTSTRAP_SERVERS,
                       help='Kafka bootstrap servers')
    
    args = parser.parse_args()
    
    # Override configuration with arguments
    if args.bootstrap_servers:
        KAFKA_BOOTSTRAP_SERVERS = args.bootstrap_servers
    if args.topic:
        KAFKA_TOPIC = args.topic
    if args.file:
        INPUT_FILE = args.file
    if args.delay:
        MESSAGE_DELAY_SECONDS = args.delay
    
    main()

