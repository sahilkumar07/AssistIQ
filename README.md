# 💬 LangGraph Chatbot

An **AI-powered conversational assistant** built with **Streamlit**, **LangGraph**, and **LangChain**, featuring multi-threaded chat history, persistent storage via SQLite, and live streaming responses from **Groq Llama 3.1**.

---

## 🚀 Features and Functionalities

### 💡 Core Features
- **Multi-threaded Chat Management**
  - Each chat session is stored as a separate thread with a unique ID.
  - Easily switch between chats or start a **new conversation**.
  - Auto-generates short, meaningful titles for new chats.

- **Streaming AI Responses**
  - Real-time streaming of assistant messages for a natural chat experience.
  - Messages are saved in SQLite for persistent conversations.

- **Tool Integration (LangChain Tools)**
  - 🧮 Built-in **Calculator Tool** supporting `add`, `sub`, `mul`, `div`.
  - 🌍 **DuckDuckGo Search** integration for real-time web results.
  - Seamlessly integrated using `ToolNode` and conditional LangGraph edges.

- **Persistent State with SQLite**
  - Stores all chat threads and messages safely using `SqliteSaver`.
  - Allows chat continuation even after restarting the app.

- **Clean and Responsive UI**
  - Powered by **Streamlit’s chat components**.
  - Sidebar for chat navigation and management.
  - In-chat message streaming for smooth UX.

---

## ⚙️ Tech Stack

| Component | Technology |
|------------|-------------|
| 💬 Frontend | Streamlit |
| 🧠 AI Model | Groq Llama 3.1 (via LangChain) |
| 🔗 Framework | LangGraph + LangChain |
| 🗃️ Database | SQLite |
| 🧰 Tools | DuckDuckGo Search, Custom Calculator |
| 🔑 Environment | Python 3.10+, dotenv for key management |

---



