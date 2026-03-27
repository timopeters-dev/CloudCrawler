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
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
QUEUE_NAME = "scraping-tasks"

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
        self.parsers = {
            "books": BookParser(),
            "quotes": QuoteParser(),
            "dynamic": DynamicParser()
        }

    async def run(self):
        print(f"[*] Worker gestartet. SQS: {SQS_ENDPOINT}")
        queue_url = await self._get_queue_url()

        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            while True:
                response = self.sqs.receive_message(
                    QueueUrl=queue_url, 
                    MaxNumberOfMessages=1, 
                    WaitTimeSeconds=5
                )

                if "Messages" not in response:
                    continue

                for msg in response["Messages"]:
                    await self._process_message(client, queue_url, msg)

    async def _get_queue_url(self):
        while True:
            try:
                return self.sqs.get_queue_url(QueueName=QUEUE_NAME)["QueueUrl"]
            except Exception:
                await asyncio.sleep(2)

    async def _process_message(self, client, queue_url, msg):
        handle = msg["ReceiptHandle"]
        try:
            body = json.loads(msg["Body"])
            url, task_type = body["url"], body["type"]
            
            print(f"[+] Verarbeite {task_type}: {url}")
            res = await client.get(url)
            res.raise_for_status()

            parser = self.parsers.get(task_type)
            if not parser:
                raise ValueError(f"Parser '{task_type}' nicht gefunden")

            if task_type == "dynamic":
                data = await parser.parse(res.text, body.get("selectors", {}), body.get("row_selector"))
            else:
                data = await parser.parse(res.text)

            await self._save_results(url, data)
            self.sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=handle)

        except Exception as e:
            await self._handle_error(msg, str(e))
            self.sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=handle)

    async def _save_results(self, url, data):
        if not data:
            return
            
        timestamp = datetime.now(timezone.utc).isoformat()
        if isinstance(data, list):
            docs = [{"url": url, "data": item, "scraped_at": timestamp} for item in data]
            await self.db["results"].insert_many(docs)
        else:
            await self.db["results"].insert_one({"url": url, "data": data, "scraped_at": timestamp})

    async def _handle_error(self, msg, error_msg):
        print(f"[X] Fehler: {error_msg}")
        await self.db["failed_tasks"].insert_one({
            "msg": msg["Body"],
            "error": error_msg,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

if __name__ == "__main__":
    worker = UniversalWorker()
    asyncio.run(worker.run())
