from pymongo import MongoClient

MONGO_URI = "mongodb+srv://rebel05631:VSXSomkVXju3myLb@cluster0.jidzjl1.mongodb.net/VirtualBot?retryWrites=true&w=majority"

# Connect to cluster
client = MongoClient(MONGO_URI)
db = client["VirtualBot"]  # your database name

# 1. Drop old "id" index if exists
try:
    db.server.drop_index("id_1")
    print("✅ Dropped index id_1")
except Exception as e:
    print("ℹ️ Index not found or already dropped:", e)

# 2. Remove "id" field from all documents
result = db.server.update_many({}, {"$unset": {"id": ""}})
print(f"✅ Removed 'id' field from {result.modified_count} documents")
