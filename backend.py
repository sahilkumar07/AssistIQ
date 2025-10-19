

from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.message import add_messages
from langchain_groq import ChatGroq
import sqlite3
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool
from dotenv import load_dotenv
import os

# ------------------- Setup -------------------
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

llm = ChatGroq(
    groq_api_key=GROQ_API_KEY,
    model_name="llama-3.1-8b-instant"
)

# ------------------- Tools -------------------
search_tool = DuckDuckGoSearchRun(region="us-en")
search_tool.name = "duckduckgo_search"

@tool
def calculator(first_num: float, second_num: float, operation: str) -> dict:
    """
    Perform a basic arithmetic operation on two numbers.
    Supported operations: add, sub, mul, div
    """
    try:
        if operation == "add":
            result = first_num + second_num
        elif operation == "sub":
            result = first_num - second_num
        elif operation == "mul":
            result = first_num * second_num
        elif operation == "div":
            if second_num == 0:
                return {"error": "Division by zero is not allowed"}
            result = first_num / second_num
        else:
            return {"error": f"Unsupported operation '{operation}'"}

        return {
            "first_num": first_num,
            "second_num": second_num,
            "operation": operation,
            "result": result
        }
    except Exception as e:
        return {"error": str(e)}

tools = [search_tool, calculator]
llm_with_tools = llm.bind_tools(tools)

# ------------------- LangGraph State -------------------
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

def chat_node(state: ChatState):
    messages = state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

tool_node = ToolNode(tools)

# ------------------- SQLite Setup -------------------
conn = sqlite3.connect(database="chatbot.db", check_same_thread=False)
checkpointer = SqliteSaver(conn=conn)

cur = conn.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS threads (
    thread_id TEXT PRIMARY KEY,
    title TEXT
)
""")
conn.commit()

# ------------------- Graph -------------------
graph = StateGraph(ChatState)
graph.add_node("chat_node", chat_node)
graph.add_node("tools", tool_node)
graph.add_edge(START, "chat_node")
graph.add_conditional_edges("chat_node", tools_condition)
graph.add_edge("tools", "chat_node")

chatbot = graph.compile(checkpointer=checkpointer)

# ------------------- DB Helpers -------------------
def save_thread_title(thread_id: str, title: str):
    """Insert or update a thread title."""
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO threads (thread_id, title) VALUES (?, ?)",
        (thread_id, title),
    )
    conn.commit()

def get_thread_title(thread_id: str):
    """Fetch a thread title by ID."""
    cur = conn.cursor()
    cur.execute("SELECT title FROM threads WHERE thread_id = ?", (thread_id,))
    row = cur.fetchone()
    return row[0] if row else None

def retrieve_all_threads():
    """Return list of (thread_id, title) pairs (latest first)."""
    cur = conn.cursor()
    cur.execute("SELECT thread_id, title FROM threads ORDER BY ROWID DESC")
    return cur.fetchall()

def generate_short_title(user_message: str) -> str:
    """Use LLM to generate a short 4–8 word title."""
    prompt = f"""
    Generate a short, human-readable title (4 to 8 words)
    that summarizes this user message:
    "{user_message}"
    Return only the title.
    """
    try:
        resp = llm.invoke([HumanMessage(content=prompt)])
        title = (resp.content or "").strip()
        if not title:
            return user_message[:30]
        return title
    except Exception:
        return user_message[:30]

def delete_thread(thread_id: str):
    """Delete a thread from DB and from the checkpointer."""
    cur = conn.cursor()
    cur.execute("DELETE FROM threads WHERE thread_id = ?", (thread_id,))
    conn.commit()

    try:
        checkpointer.delete(thread_id)
    except Exception as e:
        print(f"Warning: failed to delete checkpoints for {thread_id}: {e}")

# ------------------- Safe Message Fetch -------------------
def get_clean_state(thread_id: str):
    """
    Retrieve conversation state from LangGraph but remove ToolMessages
    and tool-related metadata before returning.
    """
    try:
        state = chatbot.get_state(config={"configurable": {"thread_id": thread_id}})
        messages = state.values.get("messages", [])
        cleaned = []
        for msg in messages:
            if isinstance(msg, ToolMessage):
                continue
            content = getattr(msg, "content", "")
            if not content or "🔧" in str(content) or "Tool finished" in str(content):
                continue
            cleaned.append(msg)
        return cleaned
    except Exception as e:
        print(f"Error fetching clean state: {e}")
        return []
