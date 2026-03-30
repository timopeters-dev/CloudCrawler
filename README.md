# 🕷️ Cloud Crawler: Verteiltes Web-Scraping-System

Ein skalierbares, asynchrones und fehlertolerantes Web-Scraping-System, entwickelt im Rahmen des Moduls **"Projekt: Einführung in die Programmierung mit Python"**. 

Dieses System nutzt eine Microservice-Architektur (Producer-Consumer-Pattern), um Webseiten effizient auszulesen, strukturierte Daten zu extrahieren und flexibel auf hohe Lasten durch Auto-Scaling zu reagieren.

## ✨ Kernfunktionen

* **Asynchrones Scraping:** Hoher Durchsatz dank `asyncio` und `httpx`.
* **Verteilte Architektur:** Entkopplung von Auftragsvergabe und Verarbeitung via **Amazon SQS** (lokal emuliert durch LocalStack).
*   **Auto-Scaling:** Ein nativer Python-Autoscaler überwacht die SQS-Warteschlange und skaliert die Docker-Worker-Container dynamisch nach oben oder unten.
*   **Sicherheit & Credentials:** Das Projekt nutzt für die lokale Entwicklung (LocalStack) Standard-Zugangsdaten (`test`/`test`). In einer Produktionsumgebung würden diese durch Umgebungsvariablen oder einen Secrets Manager ersetzt.
*   **Dynamische Parser-Engine (Box-in-Box):** Flexible Extraktions-Regeln können zur Laufzeit über das Dashboard definiert werden. Unterstützt sowohl Einzelseiten als auch Listen/Tabellen durch einen kaskadierenden Selektor-Ansatz.
* **Resilienz & Dead-Letter-Queue:** Permanente Fehler (wie HTTP 404) werden abgefangen und in einer separaten MongoDB-Collection (`failed_tasks`) protokolliert, um Queue-Endlosschleifen zu verhindern.
* **Interaktives Dashboard:** Eine Echtzeit-Benutzeroberfläche auf Basis von Streamlit zur Steuerung, Überwachung und Daten-Visualisierung.

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

### Installation & Ausführung

**1. Repository öffnen:**
```bash
cd cloud_crawler
```

**2. Infrastruktur und Container starten:**
Das System wird komplett über Docker Compose orchestratiert.
```bash
docker compose up -d --build
```

**3. Dashboard aufrufen:**
👉 **[http://localhost:8501](http://localhost:8501)**

---

## 💻 Nutzung des Dashboards

### 1. Vorgefertigte Parser
Wähle den Typ `books` oder `quotes` für bekannte Testseiten (z. B. `http://books.toscrape.com`).

### 2. Dynamischer Parser (Box-in-Box Extraktion) 🆕
Der neue dynamische Parser erlaubt das Scrapen von komplexen Listen und Tabellen:

*   **Row-Selector:** Gib hier den gemeinsamen Container für sich wiederholende Elemente an (z. B. `tr.team-row` für Tabellen oder `article.product_pod` für Produktlisten).
*   **Feld-Selektoren:** Definiere die Felder relativ zur "Row" (z. B. `td.name` oder `h3 a`).
*   **Fallback:** Bleibt der Row-Selector leer, wird die gesamte Seite als ein einziger Container behandelt (ideal für einfache Info-Seiten).

Die Worker extrahieren automatisch alle gefundenen Elemente und speichern sie als separate Dokumente in der MongoDB.

## 🛑 Beenden der Anwendung

```bash
docker compose down
```

## 📂 Projektstruktur

```text
cloud_crawler/
├── docker-compose.yml       # Docker-Orchestrierung
├── Dockerfile               # Multi-Stage Build Bauplan
├── requirements.txt         # Python-Abhängigkeiten
├── dashboard.py             # Streamlit Benutzeroberfläche
├── infrastructure/
│   └── setup_sqs.py         # Initialisierung der SQS-Queue
├── tests/
│   └── test_dynamic_parser.py # Unit-Tests für die Parser-Logik
└── src/
    ├── worker.py            # Asynchrone Worker-Logik (Consumer)
    ├── autoscaler.py        # Logik für das Docker-Auto-Scaling
    └── parsers/
        ├── base.py          # Abstrakte Basisklasse
        ├── book_parser.py   # Statischer Parser (Bücher)
        ├── quote_parser.py  # Statischer Parser (Zitate)
        └── dynamic_parser.py# Neuer Box-in-Box Parser
```
