from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from Agent import stream_graph_updates
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
import os
from llm import Gemini

bot = Gemini()


class ChatRequest(BaseModel):
    message: str

class SearchRequest(BaseModel):
    query: str

app = FastAPI()

@app.post("/chat/")
async def chat(req: ChatRequest):   
    
    reply = stream_graph_updates(req.message)
    bot.ingest_response(req.message, reply)
    return {"reply": reply}





@app.post("/upload/")
async def upload_document(file: UploadFile = File(...)):
    filename = file.filename.lower()
    contents = await file.read()
    text = ""

    try:
        if filename.endswith(".txt"):
            text = contents.decode("utf-8", errors="ignore")
        elif filename.endswith(".pdf"):
            import io
            from PyPDF2 import PdfReader
            pdf = PdfReader(io.BytesIO(contents))
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        elif filename.endswith(".docx"):
            import io
            from docx import Document
            doc = Document(io.BytesIO(contents))
            text = "\n".join([para.text for para in doc.paragraphs])
        else:
            return {"status": "error", "message": "Unsupported file type."}

        bot.ingest_document(text, doc_id=file.filename)
        return {"status": "success", "message": f"{file.filename} uploaded and processed."}
    except Exception as e:
        print(e)
        return {"status": "error", "message": "Error processing file."}