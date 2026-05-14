# 🧠 Quantum RAG AI Tutor

![Status](https://img.shields.io/badge/Status-Active-brightgreen)
![Python](https://img.shields.io/badge/Python-3.14-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![Pinecone](https://img.shields.io/badge/Pinecone-Serverless-purple)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-orange)

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Visit%20Site-cyan)](https://quantum-rag-ai-tutor.vercel.app/)

An AI-powered tutor for quantum computing built on a Retrieval-Augmented Generation (RAG) pipeline. Ask questions, get structured answers, summarize documents, and explore related research papers — all grounded in real quantum computing knowledge sourced from Wikipedia, arXiv, and Quantum StackExchange.

---

## 🌐 Live Demo

**Frontend:** [https://quantum-rag-ai-tutor.vercel.app](https://quantum-rag-ai-tutor.vercel.app)  
**Backend API:** [https://quantum-rag-ai-tutor-production.up.railway.app/docs](https://quantum-rag-ai-tutor-production.up.railway.app/docs)

> Note: AI features require OpenAI credits to be available.

---

## 📌 Overview

Quantum RAG AI Tutor is a full-stack AI application that combines vector search with large language models to deliver accurate, context-aware answers about quantum computing concepts. Whether you're a student learning the basics or a researcher exploring advanced topics, the tutor retrieves the most relevant knowledge and generates clear, structured responses.

**Key capabilities:**
- Ask any question about quantum computing and get a GPT-powered answer grounded in retrieved context
- Summarize stored documents or uploaded PDFs by topic or chapter
- Explore related research papers from arXiv alongside every answer
- Query across curated knowledge from Wikipedia, arXiv, and Quantum StackExchange

---

## 🏗️ Architecture

The application is built as a three-layer pipeline:

```
┌─────────────────────────────────────────────────────────────┐
│                        DATA LAYER                           │
│                        scraper.py                           │
│                                                             │
│  StackExchange API → AWS S3 → OpenAI Embeddings → Pinecone  │
│  arXiv API         →   ↑                                    │
│  Wikipedia API     →   ↑                                    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                       BACKEND LAYER                         │
│                          main.py                            │
│                                                             │
│               FastAPI REST API — 7 endpoints                │
│         Pinecone retrieval + GPT-4o-mini generation         │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND LAYER                         │
│                      Next.js + React                        │
│                                                             │
│                 QuantumMind UI — 3 pages                    │
│             Home / Ask the Tutor / Summarize                │
└─────────────────────────────────────────────────────────────┘
```

**How it works:**
1. **Scraper** fetches data from StackExchange, arXiv, and Wikipedia → uploads to AWS S3 → generates vector embeddings using OpenAI → stores in Pinecone
2. **Backend** receives questions from the frontend → queries Pinecone for relevant context → sends context + question to GPT-4o-mini → returns answer
3. **Frontend** provides the user interface — students ask questions, select documents, and receive structured answers with related research papers

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Data Ingestion | Python, Requests, arXiv API, StackExchange API, Wikipedia API | Fetching data from web sources |
| Vector Storage | Pinecone (Serverless) | Storing and querying document embeddings |
| Cloud Storage | AWS S3 | Storing raw scraped data as JSON |
| Embeddings | OpenAI text-embedding-3-small | Converting text chunks into vectors |
| LLM | OpenAI GPT-4o-mini | Generating answers and summaries |
| Backend | FastAPI + Uvicorn | REST API server |
| Frontend | Next.js + React + TypeScript | Interactive web UI |
| UI Components | shadcn/ui + Tailwind CSS | Component library and styling |
| Deployment | Vercel | Frontend hosting |
| PDF Parsing | Unstructured.io | Extracting text from uploaded PDFs |
| Text Splitting | LangChain RecursiveCharacterTextSplitter | Chunking documents for embeddings |
| Research Papers | arXiv API | Fetching related quantum computing papers |

---

## 📂 Project Structure

```
quantum-rag-ai-tutor/
│
├── data-ingestion/
│   └── scraper.py      # Data ingestion pipeline
├── backend/
│   └── main.py         # FastAPI backend API
├── frontend/
│   ├── app/
│   │   ├── ask/page.tsx
│   │   └── summarize/page.tsx
│   ├── components/
│   ├── lib/api.ts
│   └── package.json
├── .env                # Environment variables (not committed)
├── .gitignore
├── requirements.txt    # Python dependencies
└── README.md
```

---

## 🔑 Environment Variables

Create a `.env` file in the project root with the following:

```
OPENAI_API_KEY=
PINECONE_API_KEY=
PINECONE_INDEX_NAME=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_BUCKET=
NEXT_PUBLIC_BACKEND_URL=
```

> Backend variables go in `.env`. Frontend variable (`NEXT_PUBLIC_BACKEND_URL`) goes in `frontend/.env.local` for local development or in Vercel environment settings for production.

---

## 🚀 Setup & Usage

> ⚙️ Full setup instructions coming soon as the project progresses.

---

## 📊 Project Status

| Component | Status |
|---|---|
| Data scraper | ✅ Complete |
| FastAPI backend | ✅ Complete |
| Frontend (Next.js + React) | ✅ Complete |
| Backend deployment (Railway) | ✅ Complete |
| Frontend deployment (Vercel) | ✅ Complete |
| README | 🔄 In Progress |
| Requirements.txt | ✅ Complete |

---

## 👤 Author

**Sanika Dhayabar Patil and Kunal Tibe**  
Software and AI Engineer 
