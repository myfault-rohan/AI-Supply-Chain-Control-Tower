from kafka import KafkaConsumer
import json

consumer = KafkaConsumer(
    'inventory_updates',
    bootstrap_servers=['localhost:9092'],
    auto_offset_reset='latest',
    enable_auto_commit=True,
    group_id='debug-group',
    value_deserializer=lambda x: x.decode('utf-8')
)

print("Listening for messages on 'inventory_updates'...")
for i, message in enumerate(consumer):
    print(f"Message {i}: {message.value}")
    if i >= 4:
        break
consumer.close()
