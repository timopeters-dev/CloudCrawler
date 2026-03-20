import logging
import os
import time

import boto3
from botocore.exceptions import EndpointConnectionError

# Logging konfigurieren
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class CloudManager:
    def __init__(self, endpoint_url: str = "http://localhost:4566"):
        self.endpoint_url = endpoint_url
        self.sqs = boto3.resource(
            "sqs",
            endpoint_url=self.endpoint_url,
            region_name="us-east-1",
            aws_access_key_id="test",
            aws_secret_access_key="test",
        )

    def get_or_create_queue(self, queue_name: str):
        """Erstellt die Queue, falls sie nicht existiert, und gibt sie zurück."""
        try:
            queue = self.sqs.get_queue_by_name(QueueName=queue_name)
            logger.info(f"Queue '{queue_name}' bereits vorhanden.")
            return queue
        except self.sqs.meta.client.exceptions.QueueDoesNotExist:
            logger.info(f"Erstelle Queue: {queue_name}")
            return self.sqs.create_queue(QueueName=queue_name)


if __name__ == "__main__":
    endpoint = os.getenv("SQS_ENDPOINT", "http://localstack:4566")
    manager = CloudManager(endpoint_url=endpoint)

    # Warteschleife: Wir probieren es bis zu 10-mal
    max_retries = 10
    for i in range(max_retries):
        try:
            my_queue = manager.get_or_create_queue("scraping-tasks")
            logger.info(f"Queue erfolgreich initialisiert! URL: {my_queue.url}")
            break  # Erfolgreich -> Schleife abbrechen
        except EndpointConnectionError:
            logger.warning(
                f"LocalStack noch nicht bereit (Versuch {i+1}/{max_retries}). Warte 3 Sekunden..."
            )
            time.sleep(3)
        except Exception as e:
            logger.error(f"Unerwarteter Fehler bei LocalStack: {e}")
            time.sleep(3)
    else:
        logger.error("Konnte LocalStack nach 30 Sekunden nicht erreichen. Gebe auf.")
