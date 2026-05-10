import os
from dotenv import load_dotenv
load_dotenv()

print('='*50)
print('ENV VAR CHECK:')
print(f'GROQ_API_KEY: {"SET" if os.getenv("GROQ_API_KEY") else "MISSING"}')
print(f'QDRANT_URL: {"SET" if os.getenv("QDRANT_URL") else "MISSING"}')
print(f'QDRANT_API_KEY: {"SET" if os.getenv("QDRANT_API_KEY") else "MISSING"}')
print('='*50)
