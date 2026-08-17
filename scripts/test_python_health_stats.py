import json
import os
from fastapi import HTTPException

os.environ["GROQ_API_KEY"] = ""
os.environ["QDRANT_URL"] = ""
os.environ["QDRANT_API_KEY"] = ""

from backend.main import health, read_stats, VECTOR_DB_READY

print("=== Testing /health ===")
h = health()
print("Health Data:", json.dumps(h, indent=2))

print("\n=== Testing /stats ===")
try:
    s = read_stats()
    print("Stats Status: 200")
    print("Stats Data:", json.dumps(s, indent=2))
except HTTPException as e:
    print("Stats Status:", e.status_code)
    print("Stats Data:", json.dumps({"detail": e.detail}, indent=2))
