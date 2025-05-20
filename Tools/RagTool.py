from langchain_core.tools import BaseTool
from typing import Type
from pydantic import BaseModel, PrivateAttr  

class RAGToolInput(BaseModel):
    query: str

class RAGTool(BaseTool):
    name: str = "rag_search"
    description: str = "Searches uploaded documents and chat history to retrieve relevant context."
    args_schema: Type[BaseModel] = RAGToolInput

    _gemini: any = PrivateAttr()  

    def __init__(self, gemini_instance, **kwargs):
        super().__init__(**kwargs)
        self._gemini = gemini_instance  

    def _run(self, query: str) -> str:
        context = self._gemini.hybrid_search(query)
        return context

    def _arun(self, query: str):
        raise NotImplementedError("This tool does not support async")
