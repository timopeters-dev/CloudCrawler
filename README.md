# 🕷️ Cloud Crawler: Verteiltes Web-Scraping-System

Ein skalierbares, asynchrones und fehlertolerantes Web-Scraping-System, entwickelt im Rahmen des Moduls **"Projekt: Einführung in die Programmierung mit Python"**. 

Dieses System nutzt eine Microservice-Architektur (Producer-Consumer-Pattern), um Webseiten effizient auszulesen, strukturierte Daten zu extrahieren und flexibel auf hohe Lasten durch Auto-Scaling zu reagieren.

## ✨ Kernfunktionen

* **Asynchrones Scraping:** Hoher Durchsatz dank `asyncio` und `httpx`.
* **Verteilte Architektur:** Entkopplung von Auftragsvergabe und Verarbeitung via **Amazon SQS** (lokal emuliert durch LocalStack).
* **Auto-Scaling:** Ein nativer Python-Autoscaler überwacht die SQS-Warteschlange und skaliert die Docker-Worker-Container dynamisch nach oben oder unten.
* **Dynamische Parser-Engine:** Scraping-Regeln (CSS-Selektoren) können zur Laufzeit über das Dashboard definiert werden, ohne den Quellcode zu verändern.
* **Resilienz & Dead-Letter-Queue:** Permanente Fehler (wie HTTP 404) werden abgefangen und in einer separaten MongoDB-Collection (`failed_tasks`) protokolliert, um Queue-Endlosschleifen zu verhindern.
* **Interaktives Dashboard:** Eine Echtzeit-Benutzeroberfläche auf Basis von Streamlit zur Steuerung und Datenauswertung.

## 🏗️ Systemarchitektur

1. **Dashboard (Streamlit):** Dient als Producer. Schiebt URLs und Extraktionsregeln im JSON-Format in die SQS-Queue.
2. **LocalStack (SQS):** Dient als Message Broker / Warteschlange.
3. **Autoscaler:** Überwacht die Queue-Länge und führt `docker compose up --scale worker=X` aus.
4. **Worker (Python):** Konsumieren Nachrichten, laden Webseiten asynchron herunter, parsen die Daten und speichern sie.
5. **MongoDB:** Speichert die fertigen Ergebnisse sowie Fehlerprotokolle.

---

## 🚀 Anleitung zum Starten (Getting Started)

### Voraussetzungen
Sicherstellen, dass folgende Software auf deinem System installiert ist:
* **Docker** und **Docker Compose**
* *(Optional: Git, um das Repository zu klonen)*

### Installation & Ausführung

**1. Repository klonen (oder Verzeichnis öffnen):**
```bash
git clone https://github.com/timopeters-dev/CloudCrawler.git
cd cloud_crawler
```

**2. Infrastruktur und Container starten:**
Das System wird komplett über Docker Compose orchestriert. Führe folgenden Befehl aus, um alle Services im Hintergrund zu bauen und zu starten:
```bash
docker compose up -d --build
```
*(Hinweis: Beim ersten Start lädt Docker die benötigten Images herunter und richtet die Multi-Stage Builds ein. Dies kann ein bis zwei Minuten dauern.)*

**3. Dashboard aufrufen:**
Sobald die Container laufen, ist das interaktive Dashboard unter folgender URL erreichbar:
👉 **[http://localhost:8501](http://localhost:8501)**

---

## 💻 Nutzung des Dashboards

Über das Control Panel im Dashboard können neue Scraping-Aufgaben gestartet werden:

1. **Vorgefertigte Parser testen:** Als Typ `books` oder `quotes` auswählen und  eine Basis-URL eingeben (z. B. `http://books.toscrape.com/catalogue/page-{}.html`). Gib die Anzahl der Seiten an und klicke auf "In die Queue schieben".
2. **Dynamischen Parser testen (Custom Scraping):**
   Den Typ `dynamic` wählen und  den **➕ Button** nutzen, um beliebig viele Felder anzulegen. Anschließend den gewünschten Feldnamen (z. B. `titel`) und den passenden CSS-Selektor (z. B. `h1`) eingeben. Die Worker extrahieren die Daten exakt nach diesen Vorgaben.

Unter dem Reiter **"📊 Ergebnisse"** tauchen die gescrapten Daten in Echtzeit als flache Tabelle auf.

## 🛑 Beenden der Anwendung

Um das System herunterzufahren und alle Container zu stoppen,  im Projektverzeichnis folgenden Befehl ausführen:
```bash
docker compose down
```
*(Die MongoDB-Daten bleiben durch das gemountete Volume `mongo_data` bei einem Neustart erhalten.)*

## 📂 Projektstruktur

```text
cloud_crawler/
├── docker-compose.yml       # Docker-Orchestrierung
├── Dockerfile               # Multi-Stage Build Bauplan für Worker & Autoscaler
├── requirements.txt         # Python-Abhängigkeiten
├── dashboard.py             # Streamlit Benutzeroberfläche
├── infrastructure/
│   └── setup_sqs.py         # Skript zur Initialisierung der SQS-Queue
└── src/
    ├── worker.py            # Asynchrone Worker-Logik
    ├── autoscaler.py        # Logik für das Docker-Auto-Scaling
    └── parsers/
        ├── base.py          # Abstrakte Basisklasse für das Strategie-Muster
        ├── book_parser.py   # Statischer Parser inkl. Regex-Extraktion
        ├── quote_parser.py  # Statischer Parser für Zitate
        └── dynamic_parser.py# Verarbeitet CSS-Selektoren aus der SQS-Nachricht
```
