import os
from typing import TypedDict, List, Annotated
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
import chromadb
import json
from google import genai  # Google GenAI SDK

# Define the State for LangGraph including chat history messages
class RAGState(TypedDict):
    query: str
    context: List[str]
    generation: str
    messages: Annotated[List[BaseMessage], add_messages]

class RAGPipeline:
    def __init__(self, file_path: str):
        self.file_path = file_path
        # Initialize Gemini GenAI client
        self.genai_client = genai.Client()
        self.llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite")
        self.checkpointer = MemorySaver()
        
        # Build components
        self.collection = self._build_vector_store()
        self.graph = self._build_langgraph()

    def _get_embedding(self, text: str) -> list[float]:
        """Generates vector embeddings using Gemini's text-embedding model."""
        response = self.genai_client.models.embed_content(
            model="gemini-embedding-001",
            contents=text
        )
        return response.embeddings[0].values

    def _build_vector_store(self):
        # 1. Create in-memory Chroma instance
        chroma_client = chromadb.Client()
        collection = chroma_client.get_or_create_collection(name="markdown_rag")

        # 2. Load pre-computed embeddings from root folder
        with open(self.file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 3. Populate collection instantly (takes under 1 second, zero API costs)
        collection.add(
            ids=[item["id"] for item in data],
            documents=[item["text"] for item in data],
            embeddings=[item["embedding"] for item in data]
        )   
        return collection  # Must return the collection!

    def _build_langgraph(self):
        # Define internal node functions
        def retrieve_node(state: RAGState) -> dict:
            query = state["query"]
            query_embedding = self._get_embedding(query)
            
            # Retrieve top 3 relevant chunks
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=3
            )
            retrieved_docs = results["documents"][0] if results["documents"] else []
            return {"context": retrieved_docs}

        def generate_node(state: RAGState) -> dict:
            query = state["query"]
            context = "\n\n".join(state["context"])
            
            system_prompt = SystemMessage(
                content=f"""You are a helpful assistant answering questions based on Building Regulations of Goa.
Do not mention that you are answering based on any provided document. Only if needed, ask a question to the client/user to understand their query better.
Context:
{context}"""
            )
            
            # Combine system prompt with all previous dialogue messages in state
            input_messages = [system_prompt] + state.get("messages", [])
            response = self.llm.invoke(input_messages)
            
            return {
                "generation": response.content,
                "messages": [response]
            }

        # Build Graph
        workflow = StateGraph(RAGState)
        workflow.add_node("retrieve", retrieve_node)
        workflow.add_node("generate", generate_node)

        workflow.add_edge(START, "retrieve")
        workflow.add_edge("retrieve", "generate")
        workflow.add_edge("generate", END)

        return workflow.compile(checkpointer=self.checkpointer)

    def answer_query(self, query: str, thread_id: str) -> dict:
        config = {"configurable": {"thread_id": thread_id}}
        
        initial_state = {
            "query": query,
            "context": [],
            "generation": "",
            "messages": [HumanMessage(content=query)]
        }
        
        result = self.graph.invoke(initial_state, config=config)
        
        generation = result.get("generation")
        
        if isinstance(generation, str):
            clean_answer = generation
        elif isinstance(generation, list) and generation:
            clean_answer = generation[0].get("text", "No answer generated.")
        else:
            clean_answer = "No answer generated."

        return {
            "answer": clean_answer,
            "context": result.get("context", [])
        }
