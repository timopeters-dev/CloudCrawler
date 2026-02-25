from pymongo import MongoClient
import pprint

client = MongoClient("mongodb://localhost:27017")
db = client["crawler_db"]
collection = db["results"]

print(f"[*] Dokumente in der Datenbank: {collection.count_documents({})}")
print("-" * 30)

# Zeige das neueste Dokument
latest = collection.find_one(sort=[("_id", -1)])
pprint.pprint(latest)
