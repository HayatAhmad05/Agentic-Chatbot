import gradio as gr
import requests
import os
import re
from dotenv import load_dotenv
# from api import ChatRequest, chat


load_dotenv()
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")



def respond(user_email, message, chat_history):
    payload = {"message": message, "user_id": user_email}

    try:
        r = requests.post(f"{API_URL}/chat/", json=payload)
        
        if r.status_code == 200:
            
            response = r.json()
            reply = response.get("reply", "")
            chat_history.append((message, reply))
        else:
            chat_history.append((message, "Error: Unable to get a response."))
    except Exception as e:
        print(e)
        chat_history.append((message, "Error: Unable to get a response."))
    return chat_history, ""


def upload_file(file):
    if file is None:
        return "No file uploaded."
    try:
        with open(file.name, "rb") as f:
            files = {"file": (file.name, f)}
            r = requests.post(f"{API_URL}/upload/", files=files)
            if r.status_code == 200:
                return "File uploaded and processed successfully!"
            else:
                return "Error uploading file."
    except Exception as e:
        print(e)
        return "Error uploading file."


with gr.Blocks(title="Chatbot Demo") as demo:

    gr.Markdown("## NETSOL Chatbot")
    email = gr.Textbox(label="Your email (used as user ID)")
    chatbox = gr.Chatbot()
    msg = gr.Textbox(placeholder="Type a message or search:")
    file_upload = gr.File(label="Upload a document", file_types=[".pdf", ".txt", ".docx"])
    clear = gr.Button("Clear")
    send = gr.Button("Send")
    upload_status = gr.Markdown()
    file_upload.upload(upload_file, inputs=file_upload, outputs=upload_status)
    
    msg.submit(respond, [email, msg, chatbox], [chatbox, msg])
    send.click(respond, [email, msg, chatbox], [chatbox, msg])
    clear.click(fn=lambda: "", inputs=[], outputs=msg)
    


if __name__ == "__main__":
    demo.launch(share=True)
