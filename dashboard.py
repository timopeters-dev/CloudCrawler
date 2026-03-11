import streamlit as st
import boto3
import json
import os
import pandas as pd
from pymongo import MongoClient
import matplotlib.pyplot as plt
import seaborn as sns

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
        
        for i in range(st.session_state.field_count):
            col_x, col_y = st.columns(2)
            with col_x:
                field_name = st.text_input(f"Feldname {i+1}", key=f"name_{i}")
            with col_y:
                css_selector = st.text_input(f"CSS Selektor {i+1}", key=f"sel_{i}")
                
            if field_name and css_selector:
                custom_selectors[field_name] = css_selector
        
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

# --- LIVE-DATEN & ANALYSEN (Updaten sich alle 2 Sekunden) ---
@st.fragment(run_every="2s")
def show_data():
    # Daten aus der MongoDB laden
    results_cursor = db["results"].find().sort("_id", -1).limit(200) # Limit leicht erhöht für bessere Charts
    results_list = list(results_cursor)
    
    # --- DATEN AUFBEREITEN (FLATTENING) ---
    flat_data = []
    for r in results_list:
        base_row = {"url": r.get("url", ""), "scraped_at": r.get("scraped_at", "")}
        data_field = r.get("data", {})
        
        if isinstance(data_field, list):
            for item in data_field:
                row = base_row.copy()
                if isinstance(item, dict):
                    row.update(item)
                flat_data.append(row)
        elif isinstance(data_field, dict):
            row = base_row.copy()
            row.update(data_field)
            flat_data.append(row)

    # Pandas DataFrame erstellen
    df = pd.DataFrame(flat_data) if flat_data else pd.DataFrame()

    # --- TABS FÜR DATEN, CHARTS UND FEHLER ---
    tab1, tab2, tab3 = st.tabs(["📊 Daten-Tabelle", "📈 Analysen & Charts", "⚠️ Fehler-Log"])

    # TAB 1: ROHDATEN
    with tab1:
        st.subheader("Rohdaten der gescrapten Seiten")
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Noch keine Daten vorhanden. Starte einen Scraping-Task!")

    # TAB 2: ANALYSEN & CHARTS
    with tab2:
        st.subheader("📊 Erweiterte Daten-Visualisierung")
        
        if df.empty:
            st.warning("Keine Daten zum Visualisieren vorhanden.")
        else:
            # --- 1. SCRAPING-GESCHWINDIGKEIT (TIMELINE) ---
            st.markdown("### ⏱️ Scraping-Aktivität über Zeit")
            if 'scraped_at' in df.columns:
                # Zeitstempel in echtes Pandas-Datum umwandeln
                df['scraped_at_dt'] = pd.to_datetime(df['scraped_at'])
                # Zählen, wie viele Items pro Sekunde in die DB geschrieben wurden
                timeline = df.set_index('scraped_at_dt').resample('S').size()
                # Nur die Zeiträume anzeigen, in denen auch gescrapt wurde
                timeline = timeline[timeline > 0] 
                st.line_chart(timeline)
                st.caption("Diese Kurve zeigt die parallele Arbeitskraft deiner Worker-Container.")
                st.markdown("---")

            col_links, col_rechts = st.columns(2)

            with col_links:
                # --- 2. BUCH-ANALYSEN (Seaborn Histogramm aus der Vorlesung!) ---
                if 'price' in df.columns:
                    st.markdown("### 📚 Preisverteilung (Histogramm)")
                    df_prices = df.dropna(subset=['price']).copy()
                    df_prices['price'] = pd.to_numeric(df_prices['price'], errors='coerce').dropna()
                    
                    if not df_prices.empty:
                        # Wir nutzen Matplotlib & Seaborn, genau wie in Einheit 3!
                        fig, ax = plt.subplots(figsize=(6, 4))
                        sns.histplot(df_prices['price'], bins=15, kde=True, color="skyblue", ax=ax)
                        ax.set_title('Häufigkeitsverteilung der Buchpreise')
                        ax.set_xlabel('Preis in £')
                        ax.set_ylabel('Anzahl')
                        st.pyplot(fig) # Das rendert den Matplotlib-Plot in Streamlit!
                        
                # --- 3. ZITAT-AUTOREN ---
                if 'author' in df.columns:
                    st.markdown("### ✍️ Top Autoren")
                    df_authors = df.dropna(subset=['author'])
                    author_counts = df_authors['author'].value_counts().head(7)
                    st.bar_chart(author_counts)

            with col_rechts:
                # --- 4. ZITAT-TAGS (Listen entpacken) ---
                if 'tags' in df.columns:
                    st.markdown("### 🏷️ Beliebteste Kategorien (Tags)")
                    df_tags = df.dropna(subset=['tags']).copy()
                    # Pandas Magic: Macht aus einer Liste von Tags für jedes Tag eine eigene Zeile!
                    df_exploded = df_tags.explode('tags')
                    tag_counts = df_exploded['tags'].value_counts().head(10)
                    st.bar_chart(tag_counts, color="#ffaa00")

                # --- 5. SYSTEM-GESUNDHEIT (Pie Chart) ---
                st.markdown("### ⚙️ System-Gesundheit")
                total_success = db["results"].count_documents({})
                total_errors = db["failed_tasks"].count_documents({})
                
                if total_success > 0 or total_errors > 0:
                    fig_pie, ax_pie = plt.subplots(figsize=(4, 4))
                    labels = ['Erfolgreich', 'Fehlgeschlagen']
                    sizes = [total_success, total_errors]
                    colors = ['#2ca02c', '#d62728'] # Grün und Rot
                    
                    # Ein schickes Donut-Chart (Pie Chart mit Loch)
                    ax_pie.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors,
                               wedgeprops=dict(width=0.4, edgecolor='w'))
                    ax_pie.set_title("Verhältnis erfolgreicher Tasks")
                    st.pyplot(fig_pie)

    # TAB 3: FEHLER-LOG
    with tab3:
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

# --- DANGER ZONE (In der Sidebar) ---
st.sidebar.markdown("---")
st.sidebar.subheader("⚠️ Danger Zone")

if st.sidebar.button("🗑️ Datenbank leeren", type="primary"):
    with st.spinner("Lösche alle Dokumente..."):
        db["results"].delete_many({})
        db["failed_tasks"].delete_many({})
        
    st.sidebar.success("Datenbank erfolgreich geleert!")
    st.rerun()
