# Schlankes Python-Image als Basis
FROM python:3.11-slim

# --- DER PROFI-TRICK ---
# Wir holen uns die fertigen, funktionierenden Docker-Programme 
# direkt aus dem offiziellen Docker-Image!
COPY --from=docker:cli /usr/local/bin/docker /usr/local/bin/
COPY --from=docker:cli /usr/local/libexec/docker/cli-plugins/docker-compose /usr/local/lib/docker/cli-plugins/

# Arbeitsverzeichnis im Container
WORKDIR /app

# System-Abhängigkeiten (nur das Nötigste für Python)
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

# Befehl zum Starten (wird vom Autoscaler überschrieben)
CMD ["python", "src/worker.py"]
