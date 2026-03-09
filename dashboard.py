import streamlit as st
import boto3
import json
import os
import pandas as pd
from pymongo import MongoClient

# --- Konfiguration ---
SQS_ENDPOINT = os.getenv("SQS_ENDPOINT", "http://localhost:4566")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
QUEUE_NAME = "scraping-tasks"

st.set_page_config(page_title="Cloud Crawler Dashboard", page_icon="🕷️", layout="wide")

# --- Verbindungen ---
@st.cache_resource
def get_sqs_client():
    return boto3.client('sqs', endpoint_url=SQS_ENDPOINT, region_name='us-east-1',
                        aws_access_key_id="test", aws_secret_access_key="test")

@st.cache_resource
def get_mongo_db():
    client = MongoClient(MONGO_URI)
    return client["crawler_db"]

sqs = get_sqs_client()
db = get_mongo_db()

try:
    queue_url = sqs.get_queue_url(QueueName=QUEUE_NAME)['QueueUrl']
except Exception:
    queue_url = None

st.title("🕷️ Cloud Crawler Dashboard")

# --- LIVE-METRIKEN (Updaten sich alle 2 Sekunden) ---
@st.fragment(run_every="2s")
def show_metrics():
    worker_count = "N/A"
    try:
        import docker
        client = docker.from_env()
        workers = [c for c in client.containers.list() if "worker" in c.name]
        worker_count = len(workers)
    except Exception:
        pass 

    if queue_url:
        res = sqs.get_queue_attributes(QueueUrl=queue_url, AttributeNames=['ApproximateNumberOfMessages'])
        queue_length = int(res['Attributes']['ApproximateNumberOfMessages'])
    else:
        queue_length = "Offline"

    total_results = db["results"].count_documents({})
    total_errors = db["failed_tasks"].count_documents({})

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📦 SQS Queue Länge", queue_length)
    col2.metric("👷 Aktive Worker", worker_count)
    col3.metric("✅ Gescrapte Ergebnisse", total_results)
    col4.metric("❌ Fehlgeschlagene Tasks", total_errors)

# Fragment aufrufen
show_metrics()

st.markdown("---")

# --- CONTROL PANEL ---
st.subheader("🚀 Control Panel: Neue Aufgaben starten")

# Wir merken uns im Hintergrund, wie viele Felder der Nutzer haben will (Standard: 1)
if "field_count" not in st.session_state:
    st.session_state.field_count = 1

with st.container():
    col_a, col_b, col_c = st.columns([3, 1, 1])
    
    with col_a:
        base_url = st.text_input("Basis-URL", "http://books.toscrape.com/catalogue/page-{}.html")
    with col_b:
        task_type = st.selectbox("Parser-Typ", ["books", "quotes", "dynamic"])
    with col_c:
        msg_count = st.number_input("Anzahl", min_value=1, max_value=1000, value=1)

    custom_selectors = {}
    
    if task_type == "dynamic":
        st.info("🛠️ Custom Parser: Definiere beliebig viele Felder und ihre CSS-Selektoren.")
        
        # Wir generieren so viele Eingabefelder, wie im Counter stehen
        for i in range(st.session_state.field_count):
            col_x, col_y = st.columns(2)
            with col_x:
                # Wichtig: Eindeutige 'key' Argumente, damit Streamlit die Felder nicht verwechselt
                field_name = st.text_input(f"Feldname {i+1}", key=f"name_{i}")
            with col_y:
                css_selector = st.text_input(f"CSS Selektor {i+1}", key=f"sel_{i}")
                
            if field_name and css_selector:
                custom_selectors[field_name] = css_selector
        
        # Der Plus-Button erhöht den Counter und lädt die UI sofort neu
        if st.button("➕ Weiteres Feld hinzufügen"):
            st.session_state.field_count += 1
            st.rerun()

    submitted = st.button("In die Queue schieben", type="primary")
    
    if submitted:
        if not queue_url:
            st.error("SQS Queue nicht gefunden!")
        else:
            with st.spinner(f"Sende {msg_count} Aufgaben an SQS..."):
                for i in range(msg_count):
                    target_url = base_url.format(i + 1) if "{}" in base_url else base_url
                    
                    message_body = {"url": target_url, "type": task_type}
                    if task_type == "dynamic":
                        message_body["selectors"] = custom_selectors
                        
                    sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(message_body))
            st.success(f"Erfolgreich {msg_count} Tasks geschickt!")

st.markdown("---")

# --- LIVE-DATEN (Updaten sich alle 2 Sekunden) ---
@st.fragment(run_every="2s")
def show_data():
    tab1, tab2 = st.tabs(["📊 Ergebnisse", "⚠️ Fehler-Log"])

    with tab1:
        st.subheader("Neueste Ergebnisse")
        results_cursor = db["results"].find().sort("_id", -1).limit(50)
        results_list = list(results_cursor)
        
        if results_list:
            flat_data = []
            for r in results_list:
                row = {"_id": str(r["_id"]), "url": r.get("url"), "scraped_at": r.get("scraped_at")}
                if "data" in r:
                    row.update(r["data"])
                flat_data.append(row)
            df = pd.DataFrame(flat_data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Noch keine Ergebnisse in der Datenbank.")

    with tab2:
        st.subheader("Zuletzt fehlgeschlagene Tasks")
        errors_cursor = db["failed_tasks"].find().sort("_id", -1).limit(50)
        errors_list = list(errors_cursor)
        
        if errors_list:
            for e in errors_list:
                with st.expander(f"Fehler: {e.get('error', 'Unbekannt')} (Klick für Details)"):
                    st.json(e)
        else:
            st.success("Keine fehlerhaften Tasks gefunden. Alles läuft super!")

# Fragment aufrufen
show_data()
