"""
One-time script to migrate all chunks from local ChromaDB to Qdrant Cloud
"""
import os
import dotenv
dotenv.load_dotenv()

from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
from services.qdrant_service import get_all_chunks
from sentence_transformers import SentenceTransformer

# Qdrant connection
qdrant = QdrantClient(
    url=os.getenv("QDRANT_URL"),  # Your cluster endpoint
    api_key=os.getenv("QDRANT_API_KEY"),
)

# Collection name
COLLECTION_NAME = "vtu_study_companion"

# Create collection if it doesn't exist
try:
    qdrant.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    )
    print(f"✅ Created collection: {COLLECTION_NAME}")
except Exception as e:
    print(f"Collection might already exist: {e}")

# Get all chunks from local Chroma
print("📚 Loading chunks from local ChromaDB...")
chunks = get_all_chunks()  # Returns list of {"text": "...", "metadata": {...}}
print(f"Found {len(chunks)} chunks")

# Get embedding model
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# Migrate in batches
BATCH_SIZE = 100
total_migrated = 0

print("🔄 Migrating to Qdrant Cloud...")
for i in range(0, len(chunks), BATCH_SIZE):
    batch = chunks[i:i+BATCH_SIZE]
    
    points = []
    for idx, chunk in enumerate(batch):
        # Generate embedding for the chunk text
        embedding = embedding_model.encode(chunk["text"]).tolist()
        
        points.append({
            "id": i + idx,
            "vector": embedding,
            "payload": {
                "text": chunk["text"],
                "subject": chunk["metadata"].get("subject", ""),
                "unit": chunk["metadata"].get("unit", ""),
                "doc_type": chunk["metadata"].get("doc_type", ""),
                "filename": chunk["metadata"].get("filename", ""),
            }
        })
    
    qdrant.upsert(
        collection_name=COLLECTION_NAME,
        points=points,
    )
    
    total_migrated += len(batch)
    print(f"  Migrated {total_migrated}/{len(chunks)} chunks...")

print(f"✅ Migration complete! {total_migrated} chunks in Qdrant Cloud")