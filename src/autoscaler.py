import os
import subprocess
import time

import boto3

SQS_ENDPOINT = os.getenv("SQS_ENDPOINT", "http://localstack:4566")


def get_queue_length():
    sqs = boto3.client(
        "sqs",
        endpoint_url=SQS_ENDPOINT,
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )
    # Zieht die URL dynamisch
    res = sqs.get_queue_attributes(
        QueueUrl=sqs.get_queue_url(QueueName="scraping-tasks")["QueueUrl"],
        AttributeNames=["ApproximateNumberOfMessages"],
    )
    return int(res["Attributes"]["ApproximateNumberOfMessages"])


def scale_workers(count):
    print(f"[*] Skaliere auf {count} Worker...")

    # Führt den Docker-Befehl aus dem Container heraus aus
    result = subprocess.run(
        [
            "docker",
            "compose",
            "up",
            "-d",
            "--scale",
            f"worker={count}",
            "--no-recreate",
            "worker",
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"[!] Fehler: {result.stderr}")


if __name__ == "__main__":
    print("[!] Auto-Scaler gestartet (Die simple Variante!)...")
    while True:
        try:
            n_tasks = get_queue_length()
            print(f"[*] Aktuelle Queue-Länge: {n_tasks}")

            if n_tasks > 20:
                scale_workers(5)
            elif n_tasks > 0:
                scale_workers(2)
            else:
                scale_workers(1)

        except Exception as e:
            print(f"[-] Warte auf SQS... ({e})")

        time.sleep(10)
