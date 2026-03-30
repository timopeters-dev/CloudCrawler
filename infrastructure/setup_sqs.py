import logging
import os
import time
import boto3

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def setup_sqs():
    endpoint = os.getenv("SQS_ENDPOINT", "http://localstack:4566")
    sqs = boto3.resource("sqs", endpoint_url=endpoint, region_name="us-east-1",
                         aws_access_key_id="test", aws_secret_access_key="test")
    
    for _ in range(10):
        try:
            sqs.create_queue(QueueName="scraping-tasks")
            logging.info("SQS bereit")
            return
        except Exception as e:
            logging.warning(f"Versuch {_+1}/10: SQS noch nicht bereit ({e})")
            time.sleep(3)
if __name__ == "__main__":
    setup_sqs()
