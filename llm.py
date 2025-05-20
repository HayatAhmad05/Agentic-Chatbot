import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from tavily import TavilyClient
from dotenv import load_dotenv
from pymongo import MongoClient
from uuid import uuid4
from langchain_core.messages import SystemMessage
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.messages import SystemMessage
from datetime import datetime





load_dotenv()

uri = os.getenv("MONGODB_URI")
client = MongoClient(uri)
db = client["RAG-cluster"]
document_collection = db["document_chunks"]
chat_collection = db["chat_responses"]
chat_history = db["chat_history"]

try:
    client.admin.command("ping")
    print("Connected to MongoDB!")
except Exception as e:
    print("MongoDB connection failed:", e)

system_prompt = """
You are a smart assistant with access to two tools:

- Use `rag_search` to retrieve past user-uploaded documents and previous conversation memory stored in the database.
- Use `TavilySearch` for real-time web information.
...
"""


class Gemini:
    def __init__(self):
        google_api = os.getenv("GOOGLE_API_KEY")

        self.model = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=google_api
            )
        
        self.embedding_model = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",  
            google_api_key=google_api
        )

        self.doc_collection = document_collection
        self.chat_collection = chat_collection
        self.chat_history_collection = chat_history
    

    def ingest_document(self, text, doc_id=None, filename=None):
        if not doc_id:
            doc_id = str(uuid4())

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
    
        
        chunks = text_splitter.split_text(text)
        vectors = self.embedding_model.embed_documents(chunks)

        documents = [
            {
                "doc_id": doc_id,
                "chunk": chunk,
                "embedding": vector,
                "metadata": {
                    "chunk_index": idx,
                    "filename": filename,
                }
            }
            for idx, (chunk, vector) in enumerate(zip(chunks, vectors))
        ]

        self.doc_collection.insert_many(documents)
        print(f"Document '{filename or doc_id}' ingested successfully with {len(documents)} chunks.")


    def ingest_response(self, user_query, response_text):
        chat_entry = {
            "timestamp": datetime.utcnow(),
            "user_query": user_query,
            "response_text": response_text
        }
        self.chat_history_collection.insert_one(chat_entry)
        print("Chat saved to chat_history.")

    def hybrid_search(self, query, top_k=4):
    
        embedding = self.embedding_model.embed_query(query)

        text_pipeline = [
            {
                "$search": {
                    "text": {
                        "query": query,
                        "path": "chunk"
                    }
                }
            },
            {"$limit": top_k}
        ]

        vector_pipeline = [
            {
                "$search": {
                    "knnBeta": {
                        "vector": embedding,
                        "path": "embedding",
                        "k": top_k
                    }
                }
            },
            {"$limit": top_k}
        ]

        doc_results_text = list(self.doc_collection.aggregate(text_pipeline))
        doc_results_vec = list(self.doc_collection.aggregate(vector_pipeline))

        doc_chunks = list(set(
            doc["chunk"] for doc in doc_results_text + doc_results_vec if "chunk" in doc
        ))

        recent_chats = list(
            self.chat_history_collection.find()
            .sort("timestamp", -1)
            .limit(20)
        )[::-1]  

        chat_chunks = [
            f"User: {entry['user_query']}\nBot: {entry['response_text']}"
            for entry in recent_chats if "user_query" in entry and "response_text" in entry
        ]

        return {
            "documents": doc_chunks,
            "memory": chat_chunks
        }
