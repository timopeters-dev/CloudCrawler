# GEMINI.md - Cloud Crawler

## Project Overview
**Cloud Crawler** is a scalable, asynchronous, and fault-tolerant distributed web scraping system built with Python. It follows a microservice architecture (Producer-Consumer pattern) to efficiently extract structured data from web pages.

### Key Technologies
- **Python 3.11+**: Core language using `asyncio` and `httpx` for high-concurrency scraping.
- **Microservices**: Decoupled components communicating via **Amazon SQS** (emulated locally by **LocalStack**).
- **Auto-Scaling**: A native Python autoscaler that monitors SQS queue depth and dynamically adjusts the number of Docker worker containers.
- **Dashboard**: A real-time UI built with **Streamlit** for task management, monitoring, and data visualization (using `matplotlib` and `seaborn`).
- **Database**: **MongoDB** for storing extracted results and tracking failed tasks (`failed_tasks` collection).
- **Containerization**: Entirely orchestrated using **Docker Compose**.

### Architecture
1.  **Dashboard (Streamlit)**: Acts as the producer, pushing URLs and extraction rules (JSON) to SQS.
2.  **LocalStack (SQS)**: The message broker holding scraping tasks.
3.  **Autoscaler**: A background service that runs `docker compose up --scale worker=X` based on queue length.
4.  **Worker (Python)**: Asynchronous consumers that fetch HTML, parse it, and save results to MongoDB.
5.  **MongoDB**: Persistent storage for results and dead-letter-queue-style error logging.

---

## Building and Running

### Prerequisites
- Docker & Docker Compose

### Commands
- **Start all services**: `docker compose up -d --build`
- **Stop all services**: `docker compose down`
- **View logs**: `docker compose logs -f`
- **Scale workers manually**: `docker compose up -d --scale worker=5`
- **Access Dashboard**: Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## Development Conventions

### Code Structure
- **`src/`**: Main source code directory.
- **`src/parsers/`**: Strategy-based parsing logic. All parsers should inherit from `BaseParser` in `base.py`.
- **`src/worker.py`**: The main entry point for worker containers.
- **`src/autoscaler.py`**: Logic for dynamic scaling via the Docker socket.
- **`dashboard.py`**: Streamlit application entry point.

### Parsing Strategy
The system uses a Strategy Pattern for parsing:
- **Static Parsers**: Pre-defined logic for specific sites (e.g., `BookParser`, `QuoteParser`).
- **Dynamic Parser**: Uses CSS selectors provided in the SQS message body to extract data without code changes.

### Error Handling & Resilience
- **Poison Pill Strategy**: Permanent errors (e.g., HTTP 404) are caught by the worker, logged to the `failed_tasks` collection in MongoDB, and the message is deleted from SQS to prevent infinite loops.
- **Retries**: Temporary errors (e.g., HTTP 5xx) trigger automatic SQS visibility timeout retries.

### Docker Multi-Stage & CLI
The `Dockerfile` includes the Docker CLI and Compose plugin, allowing services like the `autoscaler` and `dashboard` to interact with the host's Docker engine via the `/var/run/docker.sock` volume mount.

### Environment Variables
Key variables used across services:
- `SQS_ENDPOINT`: URL for LocalStack SQS (default: `http://localstack:4566` in Docker).
- `MONGO_URI`: MongoDB connection string (default: `mongodb://mongodb:27017` in Docker).
- `PYTHONPATH`: Set to `/app/src` within containers to facilitate module imports.
