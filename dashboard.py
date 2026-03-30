import json
import os
import boto3
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pymongo import MongoClient

SQS_ENDPOINT = os.getenv("SQS_ENDPOINT", "http://localhost:4566")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
QUEUE_NAME = "scraping-tasks"

st.set_page_config(page_title="Cloud Crawler", page_icon="🕷️", layout="wide")

@st.cache_resource
def get_clients():
    sqs = boto3.client("sqs", endpoint_url=SQS_ENDPOINT, region_name="us-east-1", 
                       aws_access_key_id="test", aws_secret_access_key="test")
    mongo = MongoClient(MONGO_URI)["crawler_db"]
    return sqs, mongo

sqs, db = get_clients()

def get_queue_url():
    try:
        return sqs.get_queue_url(QueueName=QUEUE_NAME)["QueueUrl"]
    except:
        return None

queue_url = get_queue_url()

st.title("🕷️ Cloud Crawler Dashboard")

@st.fragment(run_every="2s")
def show_metrics():
    q_len, w_count = 0, "N/A"
    if queue_url:
        res = sqs.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["ApproximateNumberOfMessages"])
        q_len = int(res["Attributes"]["ApproximateNumberOfMessages"])
    
    try:
        import docker
        client = docker.from_env()
        w_count = len([c for c in client.containers.list() if "worker" in c.name])
    except: pass

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Warteschlange", q_len)
    c2.metric("Worker", w_count)
    c3.metric("Ergebnisse", db["results"].count_documents({}))
    c4.metric("Fehler", db["failed_tasks"].count_documents({}))

show_metrics()
st.divider()

st.subheader("🚀 Neue Aufgabe")
with st.container():
    c_type, c_url, c_count = st.columns([1, 3, 1])
    p_type = c_type.selectbox("Parser", ["books", "quotes", "dynamic"])
    
    # Default URLs
    default_urls = {
        "books": "http://books.toscrape.com/catalogue/page-{}.html",
        "quotes": "https://quotes.toscrape.com/page/{}/",
        "dynamic": "https://www.scrapethissite.com/pages/forms/?page_num={}"
    }

    # Change Detection & Presets
    if "last_p_type" not in st.session_state:
        st.session_state.last_p_type = p_type

    if st.session_state.last_p_type != p_type:
        st.session_state.last_p_type = p_type
        if p_type == "dynamic":
            st.session_state.field_keys = [0, 1, 2]
            st.session_state.f_0, st.session_state.s_0 = "name", "td.name"
            st.session_state.f_1, st.session_state.s_1 = "wins", "td.wins"
            st.session_state.f_2, st.session_state.s_2 = "losses", "td.losses"
            st.session_state.row_sel_val = "tr.team"
        st.rerun()

    url = c_url.text_input("URL", default_urls.get(p_type, ""))
    count = c_count.number_input("Anzahl", 1, 1000, 1)

    selectors, row_sel = {}, None
    if p_type == "dynamic":
        row_sel = st.text_input("Row Selector (optional)", 
                               value=st.session_state.get("row_sel_val", ""), 
                               placeholder="z.B. tr.team")
        if "field_keys" not in st.session_state: st.session_state.field_keys = [0]
        
        for i in st.session_state.field_keys:
            c_f, c_s, c_del = st.columns([2, 2, 0.5])
            fname = c_f.text_input(f"Feld", key=f"f_{i}", label_visibility="collapsed", placeholder="Feldname")
            fsel = c_s.text_input(f"Selektor", key=f"s_{i}", label_visibility="collapsed", placeholder="CSS Selektor")
            if c_del.button("🗑️", key=f"del_{i}"):
                st.session_state.field_keys.remove(i)
                st.rerun()
            if fname and fsel: selectors[fname] = fsel
            
        if st.button("➕ Feld hinzufügen"):
            new_key = max(st.session_state.field_keys) + 1 if st.session_state.field_keys else 0
            st.session_state.field_keys.append(new_key)
            st.rerun()

    if st.button("Starten", type="primary"):
        if not queue_url:
            st.error("SQS Offline")
        else:
            for i in range(count):
                t_url = url.format(i + 1) if "{}" in url else url
                payload = {"url": t_url, "type": p_type, "selectors": selectors, "row_selector": row_sel}
                sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(payload))
            st.success(f"{count} Tasks gesendet")

st.divider()

@st.fragment(run_every="5s")
def show_data():
    data = list(db["results"].find().sort("_id", -1).limit(100))
    flat = []
    for r in data:
        items = r["data"] if isinstance(r["data"], list) else [r["data"]]
        for i in items:
            flat.append({"url": r["url"], **i, "Zeit": r["scraped_at"]})
    
    df = pd.DataFrame(flat)
    t1, t2, t3 = st.tabs(["Tabelle", "Analyse", "Fehler"])
    
    with t1:
        st.dataframe(df, use_container_width=True)
    with t2:
        if df.empty:
            st.info("Noch keine Daten für eine Analyse vorhanden.")
        else:
            # --- Metriken ---
            m1, m2, m3 = st.columns(3)
            m1.metric("Eindeutige URLs", df["url"].nunique())
            m3.metric("Gescrapte Items", len(df))
            if "price" in df.columns:
                avg_p = pd.to_numeric(df["price"], errors="coerce").mean()
                m2.metric("Ø Preis", f"£{avg_p:.2f}" if not pd.isna(avg_p) else "N/A")
            
            st.divider()

            # --- Timeline: Scraping Aktivität ---
            st.subheader("⏱️ Scraping-Aktivität")
            df["dt"] = pd.to_datetime(df["Zeit"])
            timeline = df.set_index("dt").resample("10S").size()
            st.line_chart(timeline)

            st.divider()

            # --- Spalten-Layout für Charts ---
            c1, c2 = st.columns(2)

            with c1:
                if "price" in df.columns:
                    st.subheader("💰 Preisverteilung")
                    prices = pd.to_numeric(df["price"], errors="coerce").dropna()
                    if not prices.empty:
                        fig, ax = plt.subplots(figsize=(6, 4))
                        sns.histplot(prices, kde=True, color="skyblue", ax=ax)
                        st.pyplot(fig)

                if "author" in df.columns:
                    st.subheader("✍️ Top Autoren")
                    st.bar_chart(df["author"].value_counts().head(10))

            with c2:
                if "tags" in df.columns and not df.empty:
                    st.subheader("🏷️ Beliebteste Tags")
                    # Explode list of tags if they are stored as lists
                    tags_series = df.explode("tags")["tags"] if isinstance(df["tags"].iloc[0], list) else df["tags"]
                    st.bar_chart(tags_series.value_counts().head(10))
                
                # System Gesundheit
                st.subheader("⚙️ System-Status")
                s_count = db["results"].count_documents({})
                f_count = db["failed_tasks"].count_documents({})
                if s_count + f_count > 0:
                    fig, ax = plt.subplots(figsize=(4, 4))
                    ax.pie([s_count, f_count], labels=["Erfolg", "Fehler"], autopct='%1.1f%%', colors=["#2ecc71", "#e74c3c"])
                    st.pyplot(fig)
    with t3:
        errors = list(db["failed_tasks"].find().sort("_id", -1).limit(20))
        for e in errors:
            with st.expander(f"Fehler: {e.get('timestamp')}"):
                st.json(e)

show_data()

if st.sidebar.button("🗑️ Reset DB"):
    db["results"].delete_many({})
    db["failed_tasks"].delete_many({})
    st.rerun()
