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
    q_len = 0
    if queue_url:
        res = sqs.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["ApproximateNumberOfMessages"])
        q_len = int(res["Attributes"]["ApproximateNumberOfMessages"])

    c1, c2, c3 = st.columns(3)
    c1.metric("Warteschlange", q_len)
    c2.metric("Ergebnisse", db["results"].count_documents({}))
    c3.metric("Fehler", db["failed_tasks"].count_documents({}))

show_metrics()
st.divider()

st.subheader("🚀 Neue Aufgabe")
with st.container():
    c1, c2, c3 = st.columns([3, 1, 1])
    url = c1.text_input("URL", "http://books.toscrape.com/catalogue/page-{}.html")
    p_type = c2.selectbox("Parser", ["books", "quotes", "dynamic"])
    count = c3.number_input("Anzahl", 1, 1000, 1)

    selectors, row_sel = {}, None
    if p_type == "dynamic":
        row_sel = st.text_input("Row Selector (optional)", placeholder="z.B. tr.team")
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
        if not df.empty and "price" in df.columns:
            fig, ax = plt.subplots()
            sns.histplot(pd.to_numeric(df["price"], errors="coerce").dropna(), kde=True, ax=ax)
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
