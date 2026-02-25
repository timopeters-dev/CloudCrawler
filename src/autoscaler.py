import boto3
import subprocess
import time
import os

SQS_ENDPOINT = os.getenv("SQS_ENDPOINT", "http://localhost:4566")

def get_queue_length():
    sqs = boto3.client('sqs', endpoint_url=SQS_ENDPOINT, region_name='us-east-1',
                       aws_access_key_id="test", aws_secret_access_key="test")
    res = sqs.get_queue_attributes(
        QueueUrl=sqs.get_queue_url(QueueName="scraping-tasks")['QueueUrl'],
        AttributeNames=['ApproximateNumberOfMessages']
    )
    return int(res['Attributes']['ApproximateNumberOfMessages'])

def scale_workers(count):
    print(f"[*] Skaliere auf {count} Worker...")
    subprocess.run(["sudo", "docker", "compose", "up", "-d", "--scale", f"worker={count}"])
if __name__ == "__main__":
    print("[!] Auto-Scaler aktiv...")
    while True:
        try:
            n_tasks = get_queue_length()
            
            if n_tasks > 20:
                scale_workers(5)  # Maximale Auslastung
            elif n_tasks > 0:
                scale_workers(2)  # Moderate Auslastung
            else:
                scale_workers(1)  # Minimale Auslastung -> nur 1 Standby
                
        except Exception as e:
            print(f"Warte auf SQS... ({e})")
            
        time.sleep(10) # Alle 10 Sekunden prüfen
