import os
import boto3
import requests
import json
import logging
import time
import random
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec, PineconeProtocolError
from unstructured.partition.auto import partition
from unstructured.staging.base import convert_to_dict
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def init_s3():
    """Initialize and return AWS S3 client and bucket name."""
    s3 = boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name="us-east-1"
    )
    bucket_name = os.getenv("AWS_BUCKET")
    if not bucket_name:
        raise ValueError("AWS_BUCKET is not set in .env file")
    logger.info(f"S3 client initialized. Bucket: {bucket_name}")
    return s3, bucket_name

def init_pinecone():
    """Initialize and return Pinecone index."""
    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX_NAME")

    if not api_key:
        raise ValueError("PINECONE_API_KEY is not set in .env file")
    if not index_name:
        raise ValueError("PINECONE_INDEX_NAME is not set in .env file")

    pc = Pinecone(api_key=api_key)

    if index_name not in pc.list_indexes().names():
        logger.info(f"Index '{index_name}' not found. Creating...")
        pc.create_index(
            name=index_name,
            dimension=1536,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        while not pc.describe_index(index_name).status["ready"]:
            logger.info("Waiting for index to be ready...")
            time.sleep(1)

    logger.info(f"Pinecone index '{index_name}' is ready.")
    return pc.Index(index_name)

def extract_content(file_path):
    """Extract text content from various file types using Unstructured.io."""
    try:
        elements = partition(filename=file_path)
        return convert_to_dict(elements)
    except Exception as e:
        logger.error(f"Failed to extract content from {file_path}: {e}")
        return []

def split_text(text):
    """Split text into chunks using LangChain's RecursiveCharacterTextSplitter."""
    if not text.strip():
        logger.warning("Empty text passed to split_text, skipping.")
        return []
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=200,
        length_function=len,
    )
    chunks = text_splitter.split_text(text)
    logger.info(f"Split text into {len(chunks)} chunks.")
    return chunks

def fetch_arxiv():
    """Fetch latest quantum computing papers from arXiv API."""
    url = "http://export.arxiv.org/api/query"
    params = {
        "search_query": "all:quantum+computing",
        "start": 0,
        "max_results": 50,
        "sortBy": "submittedDate",
        "sortOrder": "descending"
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch arXiv papers: {e}")
        return []

    data = []
    try:
        root = ET.fromstring(response.text)
        namespace = {"atom": "http://www.w3.org/2005/Atom"}

        for entry in root.findall("atom:entry", namespace):
            try:
                title = entry.find("atom:title", namespace).text.strip()
                summary = entry.find("atom:summary", namespace).text.strip()
                link = entry.find("atom:id", namespace).text.strip()
                authors = [
                    author.find("atom:name", namespace).text.strip()
                    for author in entry.findall("atom:author", namespace)
                ]
                data.append({
                    "title": title,
                    "summary": summary,
                    "link": link,
                    "authors": ", ".join(authors),
                    "source": "arXiv"
                })
            except (AttributeError, TypeError) as e:
                logger.warning(f"Skipping arXiv entry due to parsing error: {e}")
                continue
    except ET.ParseError as e:
        logger.error(f"Failed to parse arXiv XML response: {e}")
        return []

    logger.info(f"Fetched {len(data)} papers from arXiv.")
    return data

def fetch_stackexchange():
    """Fetch top voted quantum computing questions from StackExchange API."""
    url = "https://api.stackexchange.com/2.3/questions"
    params = {
        "order": "desc",
        "sort": "votes",
        "site": "quantumcomputing",
        "pagesize": 50,
        "filter": "withbody"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch StackExchange questions: {e}")
        return []

    data = []
    for item in response.json().get("items", []):
        try:
            data.append({
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "excerpt": item.get("body", ""),
                "source": "Quantum StackExchange"
            })
        except (AttributeError, TypeError) as e:
            logger.warning(f"Skipping StackExchange item due to parsing error: {e}")
            continue

    logger.info(f"Fetched {len(data)} questions from StackExchange.")
    return data

def fetch_wikipedia():
    """Fetch quantum computing topic pages from Wikipedia API."""
    topics = [
        "Quantum computing",
        "Qubit",
        "Quantum entanglement",
        "Quantum superposition",
        "Quantum gate",
        "Quantum circuit",
        "Quantum algorithm",
        "Shor's algorithm",
        "Grover's algorithm",
        "Quantum error correction",
        "Quantum decoherence",
        "Quantum teleportation",
        "Bloch sphere",
        "Quantum Fourier transform",
        "Deutsch–Jozsa algorithm"
    ]

    url = "https://en.wikipedia.org/api/rest_v1/page/summary/"
    data = []

    for topic in topics:
        try:
            response = requests.get(
                url + topic.replace(" ", "_"),
                headers={"User-Agent": "quantum-rag-tutor/1.0"},
                timeout=10
            )
            response.raise_for_status()
            page = response.json()
            data.append({
                "title": page.get("title", ""),
                "summary": page.get("extract", ""),
                "link": page.get("content_urls", {}).get("desktop", {}).get("page", ""),
                "source": "Wikipedia"
            })
            logger.info(f"Fetched Wikipedia page: {topic}")
        except requests.RequestException as e:
            logger.warning(f"Failed to fetch Wikipedia page '{topic}': {e}")
            continue

    logger.info(f"Fetched {len(data)} pages from Wikipedia.")
    return data

def upload_to_s3(data, prefix, s3, bucket_name):
    """Upload scraped data as JSON to S3 bucket."""
    if not data:
        logger.warning(f"No data to upload for prefix '{prefix}', skipping.")
        return

    filename = f"{prefix}.json"
    try:
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
        s3.upload_file(filename, bucket_name, filename)
        logger.info(f"Uploaded '{filename}' to S3 bucket '{bucket_name}'.")
    except Exception as e:
        logger.error(f"Failed to upload '{filename}' to S3: {e}")
    finally:
        if os.path.exists(filename):
            os.remove(filename)
            logger.info(f"Cleaned up local file '{filename}'.")

def safe_upsert(index, vectors, max_retries=5):
    """Safely upsert vectors into Pinecone with exponential backoff retry logic."""
    if not vectors:
        logger.warning("No vectors to upsert, skipping.")
        return

    retries = 0
    while retries < max_retries:
        try:
            index.upsert(vectors=vectors)
            logger.info(f"Successfully upserted {len(vectors)} vectors.")
            return
        except PineconeProtocolError as e:
            retries += 1
            wait_time = 2 ** retries + random.uniform(0, 1)
            logger.warning(f"PineconeProtocolError on attempt {retries}/{max_retries}. Retrying in {wait_time:.2f}s: {e}")
            time.sleep(wait_time)

    raise Exception(f"Upsert failed after {max_retries} attempts.")

def generate_embeddings(s3, bucket_name, pc_index):
    """Download files from S3, generate embeddings, and upsert into Pinecone."""
    embeddings_model = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )

    # Handle S3 pagination — list_objects_v2 returns max 1000 objects at a time
    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=bucket_name)

    for page in pages:
        for obj in page.get("Contents", []):
            key = obj["Key"]
            local_filename = key.split("/")[-1]

            logger.info(f"Processing file: {local_filename}")

            try:
                s3.download_file(bucket_name, key, local_filename)

                if local_filename.endswith(".json"):
                    with open(local_filename, "r") as f:
                        data = json.load(f)
                    for item in data:
                        text_content = f"{item.get('title', '')} {item.get('summary', '')} {item.get('excerpt', '')}"
                        chunks = split_text(text_content)
                        logger.info(f"Number of chunks for {local_filename}: {len(chunks)}")
                        for i, chunk in enumerate(chunks):
                            embedding_vector = embeddings_model.embed_query(chunk)
                            metadata = {
                                "text": chunk,
                                "file_name": local_filename,
                                "document_title": item.get("title", ""),
                            }
                            safe_upsert(pc_index, [(f"{local_filename}_chunk_{i}", embedding_vector, metadata)])
                else:
                    content_elements = extract_content(local_filename)
                    text_content = " ".join([elem.get("text", "") for elem in content_elements])
                    chunks = split_text(text_content)
                    logger.info(f"Number of chunks for {local_filename}: {len(chunks)}")
                    for i, chunk in enumerate(chunks):
                        embedding_vector = embeddings_model.embed_query(chunk)
                        metadata = {
                            "text": chunk,
                            "file_name": local_filename,
                        }
                        safe_upsert(pc_index, [(f"{local_filename}_chunk_{i}", embedding_vector, metadata)])

            except Exception as e:
                logger.error(f"Error processing {local_filename}: {e}")
            finally:
                if os.path.exists(local_filename):
                    os.remove(local_filename)
                    logger.info(f"Cleaned up local file '{local_filename}'.")

def main():
    """Orchestrate the full scraping and embedding pipeline."""
    logger.info("Starting Quantum Computing RAG pipeline...")

    # Initialize S3 and Pinecone once and pass them through
    s3, bucket_name = init_s3()
    pc_index = init_pinecone()

    # Fetch arXiv papers
    logger.info("Fetching arXiv papers...")
    arxiv_data = fetch_arxiv()
    upload_to_s3(arxiv_data, "quantum_arxiv", s3, bucket_name)

    # Fetch StackExchange questions
    logger.info("Fetching StackExchange questions...")
    stackexchange_data = fetch_stackexchange()
    upload_to_s3(stackexchange_data, "quantum_stackexchange", s3, bucket_name)

    # Fetch Wikipedia pages
    logger.info("Fetching Wikipedia pages...")
    wikipedia_data = fetch_wikipedia()
    upload_to_s3(wikipedia_data, "quantum_wikipedia", s3, bucket_name)

    # Generate embeddings for all collected data
    logger.info("Generating embeddings and upserting to Pinecone...")
    generate_embeddings(s3, bucket_name, pc_index)

    logger.info("Pipeline completed successfully.")

if __name__ == "__main__":
    main()