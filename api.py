from fastapi import FastAPI, UploadFile, File, Request
from pydantic import BaseModel
from Agent import stream_graph_updates
from logging_config import RequestIDMiddleware, logger
from dotenv import load_dotenv
from llm import Gemini

bot = Gemini()


class ChatRequest(BaseModel):
    message: str

class SearchRequest(BaseModel):
    query: str

app = FastAPI()
app.add_middleware(RequestIDMiddleware)

@app.post("/chat/")
async def chat(req: ChatRequest, request: Request):
    logger = request.state.logger
    logger.info(f"User query: {req.message}")
    reply = stream_graph_updates(req.message)
    logger.info(f"Bot response: {reply}")
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