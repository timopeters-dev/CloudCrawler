import os
import subprocess
import time
import boto3

SQS_ENDPOINT = os.getenv("SQS_ENDPOINT", "http://localstack:4566")

def get_queue_length():
    sqs = boto3.client("sqs", endpoint_url=SQS_ENDPOINT, region_name="us-east-1",
                       aws_access_key_id="test", aws_secret_access_key="test")
    url = sqs.get_queue_url(QueueName="scraping-tasks")["QueueUrl"]
    res = sqs.get_queue_attributes(QueueUrl=url, AttributeNames=["ApproximateNumberOfMessages"])
    return int(res["Attributes"]["ApproximateNumberOfMessages"])

def scale(count):
    print(f"[*] Skalierung auf {count} Worker")
    subprocess.run(["docker", "compose", "up", "-d", "--scale", f"worker={count}", "--no-recreate", "worker"])

if __name__ == "__main__":
    while True:
        try:
            n = get_queue_length()
            if n > 20: scale(5)
            elif n > 0: scale(2)
            else: scale(1)
        except Exception as e:
            print(f"[!] Fehler im Autoscaler: {e}")
        time.sleep(10)
