# Schlankes Python-Image als Basis
FROM python:3.11-slim

# Arbeitsverzeichnis im Container
WORKDIR /app

# System-Abhängigkeiten (falls nötig)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Requirements kopieren und installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Den src-Ordner in den Container kopieren
COPY src/ ./src/
COPY infrastructure/ ./infrastructure/

# PYTHONPATH setzen, damit die Imports innerhalb von src/ funktionieren
ENV PYTHONPATH=/app/src

# Befehl zum Starten des Workers
CMD ["python", "src/worker.py"]
