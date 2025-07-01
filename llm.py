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
chat_history = db["chat_history"]

try:
    client.admin.command("ping")
    print("Connected to MongoDB!")
except Exception as e:
    print("MongoDB connection failed:", e)

system_prompt = """
You are a smart assistant with access to two tools:

1. `rag_search`: Use this tool to search through uploaded documents and previous conversations. 
   - Use for questions about uploaded files, documents, or personal information
   - Use for questions that reference previous conversations
   - This tool searches your internal knowledge base

2. `TavilySearch`: Use this tool for real-time web information and current events.
   - Use for questions about current events, news, or information not in your documents
   - Use for general knowledge questions that require up-to-date information

Always try rag_search FIRST if the user is asking about uploaded documents or previous conversations.
Only use TavilySearch if rag_search doesn't find relevant information and you need external data.

When you find relevant information from rag_search, use it to answer the user's question directly.
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


    def ingest_response(self, user_query, response_text, user_id):
        chat_entry = {
            "user_id": user_id,
            "timestamp": datetime.utcnow(),
            "user_query": user_query,
            "response_text": response_text
        }
        self.chat_history_collection.insert_one(chat_entry)
        print("Chat saved to chat_history.")

    def hybrid_search(self, query, top_k=3):
        try:
            # Get embedding for vector search
            embedding = self.embedding_model.embed_query(query)
            
            doc_chunks = []
            chat_chunks = []

            # === Try MongoDB Atlas Search first ===
            try:
                # Document text search
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

                # Document vector search
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
                
                # Chat history search
                chat_pipeline = [
                    {
                        "$search": {
                            "index": "chat-history",
                            "text": {
                                "query": query,
                                "path": ["user_query", "response_text"]
                            }
                        }
                    },
                    {"$limit": top_k}
                ]

                chat_results = list(self.chat_history_collection.aggregate(chat_pipeline))
                chat_chunks = [
                    f"User: {entry['user_query']}\nBot: {entry['response_text']}"
                    for entry in chat_results if "user_query" in entry and "response_text" in entry
                ]
                
            except Exception as search_error:
                print(f"MongoDB Atlas Search failed, using fallback: {search_error}")
                
                # === Fallback to basic MongoDB queries ===
                # Simple text matching for documents
                doc_results = list(self.doc_collection.find(
                    {"chunk": {"$regex": query, "$options": "i"}},
                    {"chunk": 1}
                ).limit(top_k))
                
                doc_chunks = [doc["chunk"] for doc in doc_results if "chunk" in doc]
                
                # Simple text matching for chat history
                chat_results = list(self.chat_history_collection.find(
                    {"$or": [
                        {"user_query": {"$regex": query, "$options": "i"}},
                        {"response_text": {"$regex": query, "$options": "i"}}
                    ]},
                    {"user_query": 1, "response_text": 1}
                ).limit(top_k))
                
                chat_chunks = [
                    f"User: {entry['user_query']}\nBot: {entry['response_text']}"
                    for entry in chat_results if "user_query" in entry and "response_text" in entry
                ]

            # Format the results as a string for the LLM
            result_parts = []
            
            if doc_chunks:
                result_parts.append("=== RELEVANT DOCUMENTS ===")
                for i, chunk in enumerate(doc_chunks[:top_k], 1):
                    result_parts.append(f"Document {i}:\n{chunk}\n")
            else:
                result_parts.append("=== NO RELEVANT DOCUMENTS FOUND ===")
                
            if chat_chunks:
                result_parts.append("=== RELEVANT CHAT HISTORY ===")
                for i, chat in enumerate(chat_chunks[:top_k], 1):
                    result_parts.append(f"Conversation {i}:\n{chat}\n")
            
            final_result = "\n".join(result_parts)
            print(f"RAG Search Results:\n{final_result}")
            return final_result
            
        except Exception as e:
            print(f"Error in hybrid_search: {e}")
            return f"Error retrieving documents: {str(e)}"
    
    def test_document_search(self, query=""):
        """Test function to check if documents exist in the database"""
        try:
            # Count total documents
            doc_count = self.doc_collection.count_documents({})
            print(f"Total documents in collection: {doc_count}")
            
            # Show some sample documents
            sample_docs = list(self.doc_collection.find({}).limit(3))
            for i, doc in enumerate(sample_docs):
                print(f"Sample doc {i+1}: {doc.get('chunk', '')[:100]}...")
                print(f"  - Filename: {doc.get('metadata', {}).get('filename', 'Unknown')}")
                print(f"  - Doc ID: {doc.get('doc_id', 'Unknown')}")
            
            if query:
                print(f"\nTesting search for: {query}")
                result = self.hybrid_search(query)
                print(f"Search result: {result[:300]}...")
                
        except Exception as e:
            print(f"Error in test_document_search: {e}")
