from typing import Annotated
import os
from typing_extensions import TypedDict
from langchain_tavily import TavilySearch
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from llm import Gemini
from dotenv import load_dotenv
from Tools.BasicToolNode import BasicToolNode
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage
from langfuse import Langfuse
from llm import Gemini
from Tools.RagTool import RAGTool

load_dotenv()

langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST")
)

bot = Gemini()

system_prompt = """
You are a smart assistant with access to two tools:

- Use `rag_search` to retrieve past user-uploaded documents and previous conversation memory stored in the database. This includes any queries related to the users personal information.
- Use `TavilySearch` for real-time web information.
...
"""



tavily_api = os.getenv("TAVILY_API_KEY")
tavily_client = TavilySearch(api_key=tavily_api)

tool = TavilySearch(max_results=3, client=tavily_client)
rag_tool = RAGTool(gemini_instance=bot)
tools = [tool, rag_tool]

bot_with_tools = bot.model.bind_tools(tools)

import re

def remove_braced_text(paragraph):
    return re.sub(r'\{.*\}', '', paragraph)


class State(TypedDict):
    messages: Annotated[list, add_messages]
graph_builder = StateGraph(State)




def chatbot(state: State):
    print(f"Processing query: {state['messages'][-1].content}")

    # Inject system prompt
    from langchain_core.messages import SystemMessage
    from llm import system_prompt  

    messages = [SystemMessage(content=system_prompt)] + state["messages"]

    response = bot_with_tools.invoke(messages)

    print(f"Tool calls: {getattr(response, 'tool_calls', None)}")
    return {"messages": [response]}


graph_builder.add_node("chatbot", chatbot)

tool_node = ToolNode(tools = [tool, rag_tool])

graph_builder.add_node("tools", tool_node)

graph_builder.add_conditional_edges(
    "chatbot",
    tools_condition,
)

graph_builder.add_edge("tools", "chatbot")
graph_builder.add_edge(START, "chatbot")

graph = graph_builder.compile()








def stream_graph_updates(user_input: str):

    chunks = []
    for event in graph.stream({"messages": [{"role": "user", "content": user_input}]}):
        for value in event.values():
            msg = value["messages"][-1] #im fucking retarded
            if hasattr(msg, "content"):
                content = msg.content
            elif isinstance(msg, dict):
                content = msg.get("content", "")
            else:
                content = str(msg)
            chunks.append(content)
    SearchResponse = "".join(chunks)
    content = remove_braced_text(SearchResponse)
    return content
    

def terminal():

    while True:
        try:
            user_input = input("User: ")
            if user_input.lower() in ["quit", "exit", "q", "end", "stop"]:
                print("Goodbye!")
                break
            stream_graph_updates(user_input)
        except:
            user_input = "What do you know about LangGraph?"
            print("User: " + user_input)
            stream_graph_updates(user_input)
            break

def test_rag_direct():
    print(rag_tool.invoke({"query": "What's in the document Sayed Hayat Ahmad.pdf?"}))

    
if __name__ == "__main__":
    # test_rag_direct() 
    terminal()