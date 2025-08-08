import os
import re
import tempfile
import logging
from typing import List, Dict

import uvicorn
import requests
from dotenv import load_dotenv

# MongoDB and LangChain Integration
import pymongo
from langchain_mongodb import MongoDBAtlasVectorSearch

from fastapi import FastAPI, Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

# LangChain Core Components
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain.prompts import PromptTemplate
from langchain.schema.document import Document

# --- CONFIGURATION & INITIALIZATION ---

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()

# 1. API Security
API_BEARER_TOKEN = os.getenv("API_BEARER_TOKEN")
if not API_BEARER_TOKEN:
    raise ValueError("API_BEARER_TOKEN is not set.")

# 2. LLM & Embeddings Models
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY is not set.")

embeddings_model = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=GOOGLE_API_KEY)
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", google_api_key=GOOGLE_API_KEY, temperature=0.2)


# +++ MODIFIED SECTION: MongoDB Atlas Client Initialization +++

# Load individual connection parameters from .env file
MONGO_HOST = os.getenv("MONGO_HOST")
MONGO_USER = os.getenv("MONGO_USER")
MONGO_PASS = os.getenv("MONGO_PASS")

if not all([MONGO_HOST, MONGO_USER, MONGO_PASS]):
    raise ValueError("One or more MongoDB environment variables are not set.")

# Names for our database and collection
DB_NAME = "langchain_db"
COLLECTION_NAME = "documents"
INDEX_NAME = "vector_index" # This must match the index you created in Atlas

# Initialize MongoDB client globally
mongo_client = None
db = None
mongo_collection = None

def initialize_mongodb():
    global mongo_client, db, mongo_collection
    try:
        # Initialize the client using individual parameters
        mongo_client = pymongo.MongoClient(
            host=f"mongodb+srv://{MONGO_HOST}", # Construct the host string
            username=MONGO_USER,
            password=MONGO_PASS,
            tls=True, # Atlas connections require TLS
            authSource='admin',
            authMechanism='SCRAM-SHA-1',
            serverSelectionTimeoutMS=5000,  # 5 second timeout
            connectTimeoutMS=10000,  # 10 second timeout
            socketTimeoutMS=10000  # 10 second timeout
        )
        # Test the connection
        mongo_client.admin.command('ismaster')
        
        db = mongo_client[DB_NAME]
        mongo_collection = db[COLLECTION_NAME]
        logging.info("Connection to MongoDB Atlas successful!")
        return True
    except Exception as e:
        logging.error(f"Failed to connect to MongoDB Atlas: {e}")
        return False

# Initialize MongoDB on startup
if not initialize_mongodb():
    logging.warning("MongoDB connection failed during startup. Will retry on first request.")

# --- API DEFINITION ---
app = FastAPI(
    title="LLM System with MongoDB Atlas", 
    version="3.1.0",
    description="AI-powered document analysis system with MongoDB Atlas vector search",
    docs_url="/docs",
    redoc_url="/redoc"
)

auth_scheme = HTTPBearer()

# Health check endpoint for Render
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "LLM System with MongoDB Atlas"}

@app.get("/")
async def root():
    return {
        "message": "LLM System with MongoDB Atlas API",
        "version": "3.1.0",
        "docs": "/docs",
        "health": "/health"
    }

# --- PYDANTIC MODELS (Unchanged) ---
class QueryRequest(BaseModel):
    documents: str = Field(..., description="URL to a single PDF or DOCX document.")
    questions: List[str] = Field(..., min_items=1, description="List of questions.")

class QueryResponse(BaseModel):
    answers: List[str]

# --- DEPENDENCIES (Unchanged) ---
def verify_token(credentials: HTTPAuthorizationCredentials = Security(auth_scheme)):
    if credentials.scheme != "Bearer" or credentials.credentials != API_BEARER_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing authentication token")
    return credentials.credentials

# --- CORE LOGIC & HELPER FUNCTIONS ---
def get_document_chunks(doc_url: str) -> List[Document]:
    # This function is the same as before
    tmp_file_path = None
    try:
        file_suffix = ".pdf" if ".pdf" in doc_url.lower() else ".docx"
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_suffix) as tmp_file:
            response = requests.get(doc_url, stream=True)
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=8192):
                tmp_file.write(chunk)
            tmp_file_path = tmp_file.name

        loader = PyPDFLoader(tmp_file_path) if file_suffix == ".pdf" else Docx2txtLoader(tmp_file_path)
        documents = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200)
        doc_chunks = text_splitter.split_documents(documents)
        
        source_filename = os.path.basename(doc_url.split('?')[0])
        for chunk in doc_chunks:
            chunk.metadata["source_document"] = source_filename
            chunk.metadata["source_url"] = doc_url # Add URL for idempotency check

        return doc_chunks
    except requests.RequestException as e:
        logging.error(f"Failed to download document from {doc_url}: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to download document: {e}")
    finally:
        if tmp_file_path and os.path.exists(tmp_file_path):
            os.unlink(tmp_file_path)

def get_mongo_vector_search(doc_url: str) -> MongoDBAtlasVectorSearch:
    """
    Initializes MongoDB Atlas Vector Search, processing the document if it's not already stored.
    """
    global mongo_collection
    
    # Ensure MongoDB is connected
    if mongo_collection is None:
        if not initialize_mongodb():
            raise HTTPException(status_code=500, detail="MongoDB connection failed")
    
    # Check if this document URL has already been processed and stored
    if mongo_collection.count_documents({"metadata.source_url": doc_url}, limit=1) == 0:
        logging.info(f"Document not found in MongoDB. Processing and storing: {doc_url}")
        doc_chunks = get_document_chunks(doc_url)
        if not doc_chunks:
            raise HTTPException(status_code=400, detail="Document could not be processed.")

        # This command embeds and stores the documents in Atlas
        vector_search = MongoDBAtlasVectorSearch.from_documents(
            documents=doc_chunks,
            embedding=embeddings_model,
            collection=mongo_collection,
            index_name=INDEX_NAME
        )
    else:
        logging.info(f"Document found in MongoDB. Loading existing vector search instance.")
        # If documents already exist, just initialize the object
        vector_search = MongoDBAtlasVectorSearch(
            collection=mongo_collection,
            embedding=embeddings_model,
            index_name=INDEX_NAME
        )
    return vector_search

# --- API ENDPOINT ---
@app.post("/api/v1/hackrx/run", response_model=QueryResponse, dependencies=[Depends(verify_token)])
async def run_submission(request: QueryRequest):
    try:
        vector_search_instance = get_mongo_vector_search(request.documents)
        retriever = vector_search_instance.as_retriever(search_kwargs={'k': 5})
        
        # The rest of this logic is the same as before
        all_source_docs: Dict[str, Document] = {}
        logging.info(f"Retrieving relevant documents for {len(request.questions)} questions.")
        for question in request.questions:
            retrieved_docs = retriever.get_relevant_documents(question)
            for doc in retrieved_docs:
                all_source_docs[doc.page_content] = doc
        
        if not all_source_docs:
             answers = ["The provided context does not contain sufficient information to answer this question."] * len(request.questions)
             return QueryResponse(answers=answers)

        combined_context = "\n\n---\n\n".join(doc.page_content for doc in all_source_docs.values())
        formatted_questions = "\n".join(f"{i+1}. {q}" for i, q in enumerate(request.questions))

        final_prompt_str = f"""
        You are an expert AI assistant for analyzing legal and policy documents. Your goal is to answer a list of questions based *exclusively* on the provided context.

        **Context from the document:**
        ---
        {combined_context}
        ---

        **Questions:**
        ---
        {formatted_questions}
        ---

        **Instructions:**
        1.  Carefully read the entire context to understand the document's content.
        2.  Answer each question from the list one by one.
        3.  **Your response MUST be a numbered list**, where each number corresponds to the question number.
        4.  Each answer must be a clear, concise, and objective statement derived only from the provided context.
        5.  Write full and formal sentence instead of 2-3 words.
        5.  **CRITICAL:** If the information to answer a specific question is not in the context, you MUST write the exact phrase: "The provided context does not contain sufficient information to answer this question." for that corresponding number.
        6.  Do not add any preamble or closing remarks. Your output should begin immediately with "1."
        """
        
        logging.info("Sending batch request to the LLM.")
        llm_response = llm.invoke(final_prompt_str)
        response_text = llm_response.content

        raw_answers = re.split(r'\n\d+\.\s*', response_text)
        answers = [ans.strip() for ans in raw_answers if ans.strip()]

        if len(answers) != len(request.questions):
             logging.warning(f"LLM did not return the expected number of answers. Got {len(answers)}, expected {len(request.questions)}. Returning raw output.")
             return QueryResponse(answers=[response_text])

        return QueryResponse(answers=answers)
    except Exception as e:
        logging.error(f"An unexpected internal error occurred: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)