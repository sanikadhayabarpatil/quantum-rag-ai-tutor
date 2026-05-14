import os
import time
import requests
import json
import logging
import boto3
import xml.etree.ElementTree as ET
from typing import List, Optional, Dict
from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from unstructured.partition.auto import partition
from unstructured.staging.base import convert_to_dict
from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# FastAPI app initialization
app = FastAPI(
    title="Quantum Computing Tutor API",
    description="Backend API for the Quantum Computing RAG Application.",
    version="1.0",
)

# Allow cross-origin requests from the frontend
# Without this, the browser blocks requests from Vercel to Railway
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://quantum-rag-ai-tutor.vercel.app",  # production frontend on Vercel
        "http://localhost:3000",                      # local development
    ],
    allow_credentials=True,   # allow cookies and auth headers
    allow_methods=["*"],      # allow GET, POST, etc.
    allow_headers=["*"],      # allow all headers
)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize Pinecone
api_key = os.getenv("PINECONE_API_KEY")
index_name = os.getenv("PINECONE_INDEX_NAME")

if not api_key:
    raise ValueError("PINECONE_API_KEY is not set in environment variables.")
if not index_name:
    raise ValueError("PINECONE_INDEX_NAME is not set in environment variables.")

pc = Pinecone(api_key=api_key)

if index_name not in pc.list_indexes().names():
    logger.info(f"Index '{index_name}' not found. Creating...")
    pc.create_index(
        index_name,
        dimension=1536,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
    )

while not pc.describe_index(index_name).status["ready"]:
    logger.info("Waiting for Pinecone index to be ready...")
    time.sleep(1)

index = pc.Index(index_name)
logger.info(f"Pinecone index '{index_name}' connected successfully.")

# Initialize AWS S3
s3_client = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name="us-east-1"
)
bucket_name = os.getenv("AWS_BUCKET")
if not bucket_name:
    raise ValueError("AWS_BUCKET is not set in environment variables.")
logger.info(f"S3 client initialized. Bucket: {bucket_name}")

# Text Splitter for embeddings
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=200,
    length_function=len,
)

# Maximum file size for uploads
MAX_FILE_SIZE_MB = 5

# Pydantic - Request and Response Models
class QAModel(BaseModel):
    query: str
    context_id: Optional[str] = None

class GenericQAModel(BaseModel):
    query: str

class ResearchPaperModel(BaseModel):
    topic: str

class SummaryRequest(BaseModel):
    document_name: Optional[str] = None
    chapter_query: Optional[str] = None
    max_tokens: Optional[int] = 1000

class SaveNoteModel(BaseModel):
    title: str
    content: str

# Utility Functions
def extract_content(file_path: str) -> list:
    """Extract text content from PDF or other file types."""
    try:
        if file_path.lower().endswith(".pdf"):
            # Use pypdf for PDF extraction — no system library dependencies
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            elements = []
            for page_num, page in enumerate(reader.pages):
                text = page.extract_text()
                if text and text.strip():
                    elements.append({"text": text.strip(), "page": page_num + 1})
            logger.info(f"Extracted {len(elements)} pages from PDF '{file_path}'.")
            return elements
        else:
            elements = partition(filename=file_path)
            return convert_to_dict(elements)
    except Exception as e:
        logger.error(f"Failed to extract content from {file_path}: {e}")
        return []

def generate_embeddings(content: str, metadata: dict = None) -> int:
    """Generate embeddings for content and upsert into Pinecone."""
    try:
        embeddings_model = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        chunks = text_splitter.split_text(content)
        if not chunks:
            logger.warning("No chunks generated from content, skipping embeddings.")
            return 0
        vectors = []
        for i, chunk in enumerate(chunks):
            embedding = embeddings_model.embed_query(chunk)
            chunk_metadata = {**(metadata or {}), "text": chunk}
            vectors.append((f"{chunk_metadata.get('id', 'chunk')}_{i}", embedding, chunk_metadata))
        index.upsert(vectors)
        logger.info(f"Upserted {len(vectors)} vectors to Pinecone.")
        return len(vectors)
    except Exception as e:
        logger.error(f"Failed to generate embeddings: {e}")
        return 0

def get_relevant_passages(query: str, top_k: int = 5, context_id: str = None) -> list:
    """Query Pinecone for relevant passages based on a query."""
    try:
        embeddings_model = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        query_embedding = embeddings_model.embed_query(query)
        filter_dict = {"file_name": context_id} if context_id else None
        results = index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
            filter=filter_dict
        )
        return [result["metadata"]["text"] for result in results["matches"]]
    except Exception as e:
        logger.error(f"Failed to get relevant passages: {e}")
        return []

def extract_chapter_content(matches: list, chapter_query: str) -> str:
    """Extract relevant content for a specific chapter or topic from Pinecone matches."""
    chapter_content = []
    for match in matches:
        text = match["metadata"].get("text", "")
        chapter_indicators = [
            f"Chapter {chapter_query}",
            f"CHAPTER {chapter_query}",
            chapter_query.title(),
            chapter_query.upper()
        ]
        if any(indicator in text for indicator in chapter_indicators):
            chapter_content.append(text)

    if not chapter_content:
        logger.warning(f"No exact chapter match found for '{chapter_query}', using all matches.")
        chapter_content = [match["metadata"].get("text", "") for match in matches]

    return "\n".join(chapter_content)

async def generate_chapter_summary(content: str, chapter_query: str, max_tokens: int = 1500) -> str:
    """Generate a structured summary for a specific chapter or topic using GPT-4o-mini."""
    try:
        prompt = f"""
        Generate a comprehensive summary for the following content related to {chapter_query}.
        Focus on the main concepts, key points, and important details.
        
        Content:
        {content}
        
        Please structure the summary with these sections:
        1. Overview
        2. Key Concepts
        3. Important Details
        4. Main Takeaways
        """
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a knowledgeable assistant specializing in creating structured summaries of technical content."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {str(e)}")

async def process_uploaded_document(file: UploadFile) -> str:
    """Save uploaded file temporarily, extract content, then clean up."""
    file_path = f"temp_{file.filename}"
    try:
        with open(file_path, "wb") as f:
            f.write(await file.read())
        content_elements = extract_content(file_path)
        content = " ".join([elem.get("text", "") for elem in content_elements])
        if not content.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from uploaded file.")
        logger.info(f"Processed uploaded file '{file.filename}' — {len(content)} characters extracted.")
        return content
    except Exception as e:
        logger.error(f"Error processing uploaded file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process uploaded file: {str(e)}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Cleaned up temp file '{file_path}'.")

# API Endpoints
@app.post("/summarize-pdf/")
async def summarize_pdf(
    file: Optional[UploadFile] = File(None),
    document_name: Optional[str] = None,
    topic: Optional[str] = None,
    chapter: Optional[str] = None
):
    """Summarize an uploaded PDF or a stored document from Pinecone."""
    try:
        logger.info(f"Summarize request — document: {document_name}, topic: {topic}, chapter: {chapter}")

        if file:
            # Validate file size
            file_bytes = await file.read()
            file_size_mb = len(file_bytes) / (1024 * 1024)
            if file_size_mb > MAX_FILE_SIZE_MB:
                raise HTTPException(
                    status_code=400,
                    detail=f"File size {file_size_mb:.1f}MB exceeds the {MAX_FILE_SIZE_MB}MB limit."
                )
            await file.seek(0)
            content = await process_uploaded_document(file)

        elif document_name:
            query = chapter if chapter else topic if topic else document_name
            logger.info(f"Using query: '{query}' for document: '{document_name}'")

            embeddings_model = OpenAIEmbeddings(
                model="text-embedding-3-small",
                openai_api_key=os.getenv("OPENAI_API_KEY")
            )
            query_embedding = embeddings_model.embed_query(query)

            results = index.query(
                vector=query_embedding,
                top_k=3,
                include_metadata=True,
                filter={"file_name": document_name}
            )
            logger.info(f"Found {len(results['matches'])} matches in Pinecone.")

            if not results["matches"]:
                raise HTTPException(
                    status_code=404,
                    detail="No relevant content found for the specified document."
                )

            content = extract_chapter_content(results["matches"], chapter) if chapter else \
                      " ".join([res["metadata"]["text"] for res in results["matches"]])

            if not content.strip():
                raise HTTPException(
                    status_code=404,
                    detail="No content could be extracted from the document."
                )
        else:
            raise HTTPException(
                status_code=400,
                detail="Please provide either a file upload or a document name."
            )

        # Generate summary
        logger.info("Generating summary...")
        summary = await generate_chapter_summary(content, chapter or topic or "document")
        logger.info("Summary generated successfully.")

        return {
            "summary": summary,
            "document": document_name if document_name else file.filename if file else None,
            "chapter": chapter,
            "topic": topic
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in summarize_pdf: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error summarizing document: {str(e)}")
    
@app.post("/summarize-chapter/")
async def summarize_chapter(request: SummaryRequest):
    """Summarize a specific chapter or topic from a stored document."""
    try:
        logger.info(f"Summarize chapter request — document: {request.document_name}, query: {request.chapter_query}")

        if not request.document_name or not request.chapter_query:
            raise HTTPException(
                status_code=400,
                detail="Both document_name and chapter_query are required."
            )

        embeddings_model = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        query_embedding = embeddings_model.embed_query(request.chapter_query)
        logger.info("Generated query embedding.")

        results = index.query(
            vector=query_embedding,
            top_k=3,
            include_metadata=True,
            filter={"file_name": request.document_name}
        )
        logger.info(f"Found {len(results['matches'])} matches in Pinecone.")

        if not results["matches"]:
            raise HTTPException(
                status_code=404,
                detail="No relevant content found for the specified chapter or topic."
            )

        content = extract_chapter_content(results["matches"], request.chapter_query)
        if not content.strip():
            raise HTTPException(
                status_code=404,
                detail="No content could be extracted for the specified chapter."
            )
        logger.info(f"Extracted content length: {len(content)} characters.")

        logger.info("Generating summary...")
        summary = await generate_chapter_summary(
            content,
            request.chapter_query,
            max_tokens=request.max_tokens or 1500
        )
        logger.info("Summary generated successfully.")

        return {
            "summary": summary,
            "document": request.document_name,
            "chapter_query": request.chapter_query
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in summarize_chapter: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/summarize-document/")
async def summarize_document(request: SummaryRequest):
    """Summarize a stored document from Pinecone by document name."""
    try:
        document_name = request.document_name.strip() if request.document_name else None
        topic = request.chapter_query.strip() if request.chapter_query else None

        if not document_name:
            raise HTTPException(status_code=400, detail="document_name is required.")

        logger.info(f"Summarize document request — document: {document_name}, topic: {topic}")

        embeddings_model = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        query = topic or document_name
        query_embedding = embeddings_model.embed_query(query)

        results = index.query(
            vector=query_embedding,
            top_k=3,
            include_metadata=True,
            filter={"file_name": document_name}
        )

        if not results["matches"]:
            raise HTTPException(status_code=404, detail="No relevant content found.")

        content = " ".join([res["metadata"]["text"] for res in results["matches"]])

        if not content.strip():
            raise HTTPException(status_code=404, detail="No content could be extracted.")

        summary = await generate_chapter_summary(content, topic or document_name)

        return {
            "summary": summary,
            "document": document_name,
            "topic": topic
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in summarize_document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/qa-pdf/")
async def qa_pdf(model: QAModel):
    """Answer a question using Pinecone context and GPT-4o-mini."""
    try:
        logger.info(f"Q&A request — query: '{model.query}', context_id: '{model.context_id}'")

        # Get relevant passages from Pinecone
        passages = get_relevant_passages(
            query=model.query,
            top_k=5,
            context_id=model.context_id
        )

        if not passages:
            logger.warning("No relevant passages found in Pinecone.")
            context = ""
        else:
            context = " ".join(passages)

        # Build system prompt based on whether we have context
        if context:
            system_prompt = """You are a knowledgeable quantum computing tutor. 
            Answer the question using the provided context. 
            If the context doesn't fully answer the question, supplement with your own knowledge."""
            user_prompt = f"Context:\n{context}\n\nQuestion: {model.query}"
        else:
            system_prompt = """You are a knowledgeable quantum computing tutor. 
            Answer the question comprehensively using your knowledge."""
            user_prompt = model.query

        # Call GPT-4o-mini
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        answer = response.choices[0].message.content
        logger.info("Answer generated successfully.")

        # Fetch related arXiv papers
        papers = []
        try:
            papers_response = requests.get(
                f"http://export.arxiv.org/api/query",
                params={
                    "search_query": f"all:{model.query}",
                    "start": 0,
                    "max_results": 3
                },
                timeout=10
            )
            if papers_response.status_code == 200:
                root = ET.fromstring(papers_response.text)
                namespace = {"atom": "http://www.w3.org/2005/Atom"}
                for entry in root.findall("atom:entry", namespace):
                    title = entry.find("atom:title", namespace).text.strip()
                    link = entry.find("atom:id", namespace).text.strip()
                    papers.append({"title": title, "link": link})
        except Exception as e:
            logger.warning(f"Failed to fetch arXiv papers: {e}")

        return {
            "answer": answer,
            "papers": papers,
            "has_document_context": bool(model.context_id)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error in qa_pdf: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error in Q&A: {str(e)}")

@app.post("/generic-qa/")
async def generic_qa(model: GenericQAModel):
    """Answer a general quantum computing question without document context."""
    try:
        logger.info(f"Generic Q&A request — query: '{model.query}'")

        passages = get_relevant_passages(query=model.query, top_k=3)

        if passages:
            context = " ".join(passages)
            system_prompt = """You are a knowledgeable quantum computing tutor. 
            Use the provided context and your knowledge to answer accurately."""
            user_prompt = f"Context:\n{context}\n\nQuestion: {model.query}"
        else:
            system_prompt = """You are a knowledgeable quantum computing tutor. 
            Answer the question as accurately and clearly as possible."""
            user_prompt = model.query

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        answer = response.choices[0].message.content
        logger.info("Generic Q&A answer generated successfully.")
        return {"answer": answer}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in generic_qa: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error in generic Q&A: {str(e)}")

@app.post("/fetch-research-papers/")
async def fetch_research_papers(model: ResearchPaperModel):
    """Fetch related research papers from arXiv for a given topic."""
    try:
        logger.info(f"Fetching research papers for topic: '{model.topic}'")

        response = requests.get(
            "http://export.arxiv.org/api/query",
            params={
                "search_query": f"all:{model.topic}",
                "start": 0,
                "max_results": 5,
                "sortBy": "relevance",
                "sortOrder": "descending"
            },
            timeout=30
        )

        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to fetch research papers from arXiv.")

        papers = []
        root = ET.fromstring(response.text)
        namespace = {"atom": "http://www.w3.org/2005/Atom"}

        for entry in root.findall("atom:entry", namespace):
            try:
                title = entry.find("atom:title", namespace).text.strip()
                link = entry.find("atom:id", namespace).text.strip()
                summary = entry.find("atom:summary", namespace).text.strip()
                papers.append({
                    "title": title,
                    "link": link,
                    "summary": summary
                })
            except (AttributeError, TypeError) as e:
                logger.warning(f"Skipping arXiv entry due to parsing error: {e}")
                continue

        logger.info(f"Fetched {len(papers)} papers from arXiv.")
        return {"papers": papers}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching research papers: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching papers: {str(e)}")

@app.get("/publications/")
async def get_publications():
    """Return list of all unique data sources stored in Pinecone."""
    try:
        logger.info("Fetching publications list...")

        # Use a meaningful query instead of a zero vector
        embeddings_model = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        query_embedding = embeddings_model.embed_query("quantum computing")

        results = index.query(
            vector=query_embedding,
            top_k=10000,
            include_metadata=True
        )

        documents = {}
        for match in results.get("matches", []):
            metadata = match.get("metadata", {})
            file_name = metadata.get("file_name")
            document_title = metadata.get("document_title")
            if file_name and file_name not in documents:
                documents[file_name] = {
                    "file_name": file_name,
                    "document_title": document_title or file_name
                }

        logger.info(f"Found {len(documents)} unique sources in Pinecone.")
        return {"publications": list(documents.values())}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching publications: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching publications: {str(e)}")

@app.get("/embeddings-stats/")
async def get_embeddings_stats():
    """Return stats about the Pinecone index."""
    try:
        stats = index.describe_index_stats()
        logger.info("Fetched Pinecone index stats.")
        return {
            "total_vectors": stats.total_vector_count,
            "dimension": stats.dimension,
            "namespaces": stats.namespaces
        }
    except Exception as e:
        logger.error(f"Error getting embeddings stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/check-pinecone-index/")
async def check_index():
    """Debug endpoint — inspect what's stored in the Pinecone index."""
    try:
        embeddings_model = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        query_embedding = embeddings_model.embed_query("quantum computing")
        results = index.query(
            vector=query_embedding,
            top_k=100,
            include_metadata=True
        )
        return {
            "matches": len(results.get("matches", [])),
            "metadata": [match.get("metadata", {}) for match in results["matches"]],
        }
    except Exception as e:
        logger.exception(f"Error checking Pinecone index: {e}")
        raise HTTPException(status_code=500, detail=f"Error checking Pinecone index: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )