# 🧠 RAGChat: Retrieval-Augmented Chatbot with Gemini + FastAPI + MongoDB

A powerful and extensible chatbot that uses **Google Gemini 2.0 Flash**, **MongoDB**, **LangGraph**, and **FastAPI** to deliver conversational AI with memory and file-based document retrieval. Includes real-time internet search via **Tavily** and a custom-built `rag_search` tool.

---

## 📦 Features

- ✨ **Gemini LLM Integration**: Powered by Google's Gemini 2.0 Flash via LangChain.
- 📄 **Document Uploading & Ingestion**: Split, embed, and store user documents in MongoDB.
- 🔎 **Hybrid Search (RAG)**: Combines vector similarity and keyword search to retrieve relevant chunks.
- 🧠 **Memory Recall**: Returns recent chat history to maintain conversational context.
- 🌐 **Tavily Integration**: Enables real-time search for current events and external queries.
- 🧰 **Agent + Tools Architecture**: Uses LangGraph tools (`rag_search`, `tavily_search`) to enable agentic behavior.
- 🧾 **Logging + Request ID Middleware**: Tracks each request with unique IDs for debugging and tracing.

---

## 🛠 Tech Stack

| Layer       | Tech                                           |
|-------------|------------------------------------------------|
| LLM         | Gemini 2.0 Flash via LangChain                 |
| Backend     | FastAPI                                        |
| Search Tools| Tavily + Custom `rag_search` (LangGraph Tool) |
| Database    | MongoDB Atlas                                  |
| Embeddings  | GoogleGenerativeAIEmbeddings                   |
| Frontend    | Gradio (optional UI interface)                 |
| Logging     | Python Logging + Request ID Middleware         |
