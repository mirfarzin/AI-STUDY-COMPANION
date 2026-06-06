# VTU AI Study Companion 🎓

An AI-powered VTU study assistant that uses Retrieval-Augmented Generation (RAG) to answer questions from uploaded VTU notes, provide exam-oriented explanations, and cite supporting study material.

## Features ✨

* AI-powered question answering using VTU study materials
* Retrieval-Augmented Generation (RAG) with semantic search
* Subject-wise filtering for focused study
* Exam-oriented answer generation (5-mark and 10-mark style responses)
* Citation support with source document references
* PDF-based knowledge retrieval
* FastAPI backend with React frontend
* Railway + Vercel production deployment

---

## API Endpoints 📡

### POST `/api/chat`

Ask a question and receive a contextual answer based on indexed study materials.

### POST `/api/upload`

Upload study materials for indexing and retrieval.

### POST `/api/predict`

Generate important-question predictions.

### POST `/api/pyq`

Analyze and answer previous-year questions.

### POST `/api/weak-topics`

Identify weak topics based on user performance and interactions.

---

## Architecture 🏗️

Frontend (React + Vite)
↓
FastAPI Backend
↓
Qdrant Vector Database
↓
Groq LLM
↓
Study Materials (PDFs)

---

## Tech Stack 🛠️

| Layer      | Technology                |
| ---------- | ------------------------- |
| Frontend   | React, Vite, Tailwind CSS |
| Backend    | FastAPI, Pydantic         |
| LLM        | Groq                      |
| Vector DB  | Qdrant                    |
| Database   | PostgreSQL                |
| Deployment | Railway, Vercel           |

---

## Screenshots 📸

### Chat Interface

<img width="1557" height="717" alt="image" src="https://github.com/user-attachments/assets/44a6deb7-3135-4592-a497-9a5d19bacb0b" />


### Subject Selection
<img width="392" height="907" alt="image" src="https://github.com/user-attachments/assets/71c5068c-49a8-455f-aa22-41c22fdbfefa" />


---



## Author 👨‍💻

Built by Mir Farzin

B.E. CSE (AI & ML)
M. S. Ramaiah Institute of Technology (MSRIT)

GitHub:
https://github.com/mirfarzin
