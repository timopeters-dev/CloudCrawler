import os
import boto3
import json

# --- Konfiguration ---
SQS_ENDPOINT = os.getenv("SQS_ENDPOINT", "http://localhost:4566")
REGION = "us-east-1"
QUEUE_NAME = "scraping-tasks"

class ScrapingProducer:
    def __init__(self):
        # Verbindung zu LocalStack SQS
        self.sqs = boto3.client(
            'sqs', 
            endpoint_url=SQS_ENDPOINT, 
            region_name=REGION,
            aws_access_key_id="test", 
            aws_secret_access_key="test"
        )
        
        # Wir holen uns die URL der Queue anhand des Namens
        try:
            response = self.sqs.get_queue_url(QueueName=QUEUE_NAME)
            self.queue_url = response['QueueUrl']
        except Exception:
            print(f"[-] Queue '{QUEUE_NAME}' nicht gefunden. Starte erst LocalStack/Infrastructure!")
            exit(1)

    def send_task(self, url, task_type="books"):
        """Packt eine URL in die Queue."""
        message_body = {
            "url": url,
            "type": task_type
        }
        
        self.sqs.send_message(
            QueueUrl=self.queue_url,
            MessageBody=json.dumps(message_body)
        )
        print(f"[+] Task gesendet: {url} ({task_type})")

# --- Test-Lauf ---
if __name__ == "__main__":
    producer = ScrapingProducer()
    print("[*] Starte Massen-Versand...")
    for i in range(50):
        url = f"http://books.toscrape.com/catalogue/page-{ (i % 50) + 1 }.html"
        producer.send_task(url, task_type="books")    
    print("[*] Fertig! Die Worker können jetzt loslegen.")
