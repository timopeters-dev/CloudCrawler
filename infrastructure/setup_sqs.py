import boto3
import logging

# Logging konfigurieren, damit wir sehen, was passiert
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class CloudManager:
    def __init__(self, endpoint_url: str = "http://localhost:4566"):
        self.endpoint_url = endpoint_url
        # Wir erstellen einen SQS "Resource" Client
        # Region 'us-east-1' ist bei LocalStack Standard
        self.sqs = boto3.resource(
            'sqs',
            endpoint_url=self.endpoint_url,
            region_name="us-east-1",
            aws_access_key_id="test",
            aws_secret_access_key="test"
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
    import os
    # SQS_ENDPOINT kommt aus der docker-compose environment Sektion
    endpoint = os.getenv("SQS_ENDPOINT", "http://localstack:4566")
    manager = CloudManager(endpoint_url=endpoint)
    # WICHTIG: Name muss mit dem Worker übereinstimmen!
    my_queue = manager.get_or_create_queue("scraping-tasks") 
    print(f"Queue URL: {my_queue.url}")
