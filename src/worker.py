import os
import asyncio
import json
import boto3
import httpx
from motor.motor_asyncio import AsyncIOMotorClient
from parsers.book_parser import BookParser
from parsers.quote_parser import QuoteParser

# --- Konfiguration ---
SQS_ENDPOINT = os.getenv("SQS_ENDPOINT", "http://localhost:4566")
QUEUE_NAME = "scraping-tasks"
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")

class UniversalWorker:
    def __init__(self):
        self.sqs = boto3.client(
            'sqs', 
            endpoint_url=SQS_ENDPOINT, 
            region_name='us-east-1',
            aws_access_key_id="test",
            aws_secret_access_key="test"
        )
        self.mongo = AsyncIOMotorClient(MONGO_URI)
        self.db = self.mongo["crawler_db"]
        
        self.parsers = {
            "books": BookParser(),
            "quotes": QuoteParser()
        }

    async def process_single_message(self, msg, http_client, queue_url):
        """Verarbeitet genau eine Nachricht. Läuft parallel zu anderen."""
        receipt_handle = msg['ReceiptHandle']
        
        try:
            body = json.loads(msg['Body'])
            url = body['url']
            task_type = body['type']
            
            print(f"[+] Verarbeite {task_type}: {url}")

            res = await http_client.get(url, timeout=10.0)
            res.raise_for_status() 
            
            parser = self.parsers.get(task_type)
            if not parser:
                raise ValueError(f"Kein Parser für Typ '{task_type}' gefunden!")

            data = await parser.parse(res.text)

            await self.db["results"].insert_one({
                "url": url,
                "data": data,
                "scraped_at": "2026-03-06" # Angepasst an dein Datumsformat
            })
            
            # Nachricht aus Queue löschen nach Erfolg
            self.sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
            print(f"[V] Erledigt: {url}")

        except json.JSONDecodeError:
            print(f"[!] Kritischer Fehler: Ungültiges JSON. Lösche Nachricht.")
            self.sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)

        except ValueError as ve:
            print(f"[!] Logik-Fehler: {ve}. Speichere in DB und lösche Nachricht.")
            await self.db["failed_tasks"].insert_one({"error": str(ve), "msg": msg['Body']})
            self.sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)

        except Exception as e:
            # Temporärer Fehler (Netzwerk, etc.). Kein Löschen -> Retry durch SQS
            print(f"[-] Temporärer Fehler bei {receipt_handle[:10]}: {e}. Retry folgt.")


    async def run(self):
        print("[*] Worker gestartet. Warte auf Aufgaben in SQS...")
        queue_url = None
        while not queue_url:
            try:
                queue_url = self.sqs.get_queue_url(QueueName=QUEUE_NAME)['QueueUrl']
            except Exception:
                print(f"[-] Queue '{QUEUE_NAME}' noch nicht bereit. Warte 2 Sekunden...")
                await asyncio.sleep(2)
    
        print(f"[+] Queue gefunden: {queue_url}. Warte auf Aufgaben...")

        async with httpx.AsyncClient() as http_client:
            while True:
                # Wir holen jetzt bis zu 10 Nachrichten auf einmal!
                response = self.sqs.receive_message(
                    QueueUrl=queue_url,
                    MaxNumberOfMessages=10, 
                    WaitTimeSeconds=5
                )

                messages = response.get('Messages', [])
                if not messages:
                    continue
                
                print(f"[*] {len(messages)} Nachrichten empfangen. Starte parallele Verarbeitung...")

                # Erstelle Tasks für alle empfangenen Nachrichten
                tasks = [
                    self.process_single_message(msg, http_client, queue_url) 
                    for msg in messages
                ]
                
                # Führe alle Tasks gleichzeitig aus und warte, bis alle fertig sind
                await asyncio.gather(*tasks)


if __name__ == "__main__":
    worker = UniversalWorker()
    asyncio.run(worker.run())
