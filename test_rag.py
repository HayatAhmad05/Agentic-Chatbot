#!/usr/bin/env python3
"""
Test script to verify RAG functionality
"""

from llm import Gemini
from Tools.RagTool import RAGTool

def test_rag_setup():
    print("=== Testing RAG Setup ===")
    
    # Initialize Gemini
    bot = Gemini()
    
    # Test database connection and document count
    bot.test_document_search()
    
    # Test RAG tool
    rag_tool = RAGTool(gemini_instance=bot)
    
    print("\n=== Testing RAG Tool ===")
    test_queries = [
        "What documents do you have?",
        "Tell me about the uploaded files",
        "What's in the documents?"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        try:
            result = rag_tool.invoke({"query": query})
            print(f"Result: {result[:200]}...")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test_rag_setup()
