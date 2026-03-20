import asyncio
import json
import os
from datetime import datetime, timezone

import boto3
import httpx
from motor.motor_asyncio import AsyncIOMotorClient

from parsers.book_parser import BookParser
from parsers.dynamic_parser import DynamicParser
from parsers.quote_parser import QuoteParser

SQS_ENDPOINT = os.getenv("SQS_ENDPOINT", "http://localhost:4566")
QUEUE_NAME = "scraping-tasks"
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")


class UniversalWorker:
    def __init__(self):
        self.sqs = boto3.client(
            "sqs",
            endpoint_url=SQS_ENDPOINT,
            region_name="us-east-1",
            aws_access_key_id="test",
            aws_secret_access_key="test",
        )
        self.mongo = AsyncIOMotorClient(MONGO_URI)
        self.db = self.mongo["crawler_db"]

        self.parsers = {"books": BookParser(), "quotes": QuoteParser()}

    async def run(self):
        print("[*] Standard-Worker gestartet. Warte auf Aufgaben...")
        queue_url = None
        while not queue_url:
            try:
                queue_url = self.sqs.get_queue_url(QueueName=QUEUE_NAME)["QueueUrl"]
            except Exception:
                await asyncio.sleep(2)

        async with httpx.AsyncClient(follow_redirects=True) as http_client:
            while True:
                response = self.sqs.receive_message(
                    QueueUrl=queue_url, MaxNumberOfMessages=1, WaitTimeSeconds=5
                )

                if "Messages" not in response:
                    continue

                for msg in response["Messages"]:
                    receipt_handle = msg["ReceiptHandle"]

                    try:
                        body = json.loads(msg["Body"])
                        url = body["url"]
                        task_type = body["type"]

                        print(f"[+] WORKER Verarbeite {task_type}: {url}")

                        res = await http_client.get(url, timeout=10.0)
                        res.raise_for_status()

                        if task_type == "dynamic":
                            # Dynamischer Parser zieht sich die Selektoren aus der SQS Nachricht
                            parser = DynamicParser()
                            selectors = body.get("selectors", {})
                            data = await parser.parse(res.text, selectors)
                        else:
                            parser = self.parsers.get(task_type)
                            if not parser:
                                raise ValueError(
                                    f"Kein Parser für Typ '{task_type}' gefunden!"
                                )
                            data = await parser.parse(res.text)

                        current_time = datetime.now(timezone.utc).isoformat()

                        # --- LOGIK FÜR LISTEN (Multi-Item-Extractor) ---
                        if isinstance(data, list):
                            if len(data) > 0:
                                # Fall A: Erfolgreich Elemente gefunden
                                documents = [
                                    {
                                        "url": url,
                                        "data": item,
                                        "scraped_at": current_time,
                                    }
                                    for item in data
                                ]
                                await self.db["results"].insert_many(documents)
                                print(
                                    f"[V] WORKER Erledigt! {len(documents)} Items von {url} extrahiert."
                                )
                            else:
                                # Fall B: POISON PILL ABFANGEN (Seite ok, aber keine Elemente)
                                print(
                                    f"[!] WORKER Warnung: Keine passenden Elemente auf {url} gefunden."
                                )
                                await self.db["failed_tasks"].insert_one(
                                    {
                                        "url": url,
                                        "error": "Keine passenden HTML-Elemente gefunden (Leere Liste)",
                                        "timestamp": current_time,
                                    }
                                )
                        else:
                            # Fall C: Fallback für einzelne Dictionaries
                            await self.db["results"].insert_one(
                                {"url": url, "data": data, "scraped_at": current_time}
                            )
                            print(f"[V] WORKER Erledigt! 1 Item extrahiert.")

                        # GANZ WICHTIG: Die Nachricht MUSS immer gelöscht werden,
                        # egal ob Fall A, B oder C eingetreten ist!
                        self.sqs.delete_message(
                            QueueUrl=queue_url, ReceiptHandle=receipt_handle
                        )

                    except json.JSONDecodeError:
                        self.sqs.delete_message(
                            QueueUrl=queue_url, ReceiptHandle=receipt_handle
                        )

                    except ValueError as ve:
                        await self.db["failed_tasks"].insert_one(
                            {"error": str(ve), "msg": msg["Body"]}
                        )
                        self.sqs.delete_message(
                            QueueUrl=queue_url, ReceiptHandle=receipt_handle
                        )

                    except httpx.HTTPStatusError as http_err:
                        status = http_err.response.status_code
                        if 400 <= status < 500:
                            print(
                                f"[!] Permanenter HTTP Fehler {status} bei {url}. Breche ab."
                            )
                            await self.db["failed_tasks"].insert_one(
                                {
                                    "error": f"HTTP {status} (Not Found / Forbidden)",
                                    "url": url,
                                }
                            )
                            self.sqs.delete_message(
                                QueueUrl=queue_url, ReceiptHandle=receipt_handle
                            )
                        else:
                            print(
                                f"[-] Temporärer Server-Fehler {status} bei {url}. Retry folgt automatisch."
                            )

                    except Exception as e:
                        # 1. FEHLER PROTOKOLLIEREN (Dead-Letter-Queue)
                        error_msg = str(e)
                        print(f"[X] WORKER Exception bei {url}: {error_msg}")

                        # WICHTIG: await nutzen, da motor asynchron ist!
                        await self.db["failed_tasks"].insert_one(
                            {
                                "url": url,
                                "error": error_msg,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            }
                        )

                        # 2. DIE POISON PILL LÖSCHEN! (Das stoppt das Rotieren)
                        self.sqs.delete_message(
                            QueueUrl=queue_url, ReceiptHandle=receipt_handle
                        )
                        print(f"[!] WORKER Poison Pill gelöscht: {url}")


if __name__ == "__main__":
    worker = UniversalWorker()
    asyncio.run(worker.run())
