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

from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages

load_dotenv()

langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST")
)

bot = Gemini()

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
    print(f"Response content: {getattr(response, 'content', 'No content')}")
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
    tool_results = []
    print(f"Starting stream for: {user_input}")
    
    for event in graph.stream({"messages": [{"role": "user", "content": user_input}]}):
        print(f"Event: {list(event.keys())}")
        for node_name, value in event.items():
            if node_name == "tools":
                # Skip tool output, we only want the final chatbot response
                tool_results.append(value["messages"][-1].content)
                print(f"Tool executed: {tool_results[-1][:100]}...")
            elif node_name == "chatbot":
                msg = value["messages"][-1]
                if hasattr(msg, "content") and msg.content:
                    content = msg.content
                    # Only add content that's not a tool call (actual response)
                    if content and not hasattr(msg, 'tool_calls') or (hasattr(msg, 'tool_calls') and not msg.tool_calls):
                        chunks.append(content)
                        print(f"Added final response: {content[:100]}...")
    
    if chunks:
        final_response = "".join(chunks)
    else:
        # Fallback if no final response was captured
        final_response = "I apologize, but I couldn't process your request properly."
    
    content = remove_braced_text(final_response)
    print(f"Final response: {content[:200]}...")
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