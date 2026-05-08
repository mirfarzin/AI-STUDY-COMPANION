from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import upload, chat, predict, pyq, sync

app = FastAPI(title="VTU Study Companion API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(chat.router)
app.include_router(predict.router)
app.include_router(pyq.router)
app.include_router(sync.router)

from services.chroma_service import get_collection_stats

@app.get("/stats")
def read_stats():
    return get_collection_stats()

@app.get("/")
def root():
    return {"message": "VTU Study Companion API is running"}
