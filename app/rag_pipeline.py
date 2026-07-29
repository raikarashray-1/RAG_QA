import os
from typing import TypedDict, List, Annotated
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
import chromadb
from google import genai

# Define the updated State for LangGraph
class RAGState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    context: List[str]
    standalone_query: str

class RAGPipeline:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.genai_client = genai.Client()
        self.llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite") # or your preferred Gemini model
        
        self.collection = self._build_vector_store()
        # Create an in-memory checkpointer for session state
        self.memory = MemorySaver()
        self.graph = self._build_langgraph()

    def _get_embedding(self, text: str) -> list[float]:
        response = self.genai_client.models.embed_content(
            model="gemini-embedding-001",
            contents=text
        )
        return response.embeddings[0].values

    def _build_vector_store(self):
        with open(self.file_path, "r", encoding="utf-8") as f:
            markdown_content = f.read()

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            separators=["\n## ", "\n### ", "\n\n", "\n", " "]
        )

        chunks = text_splitter.split_text(markdown_content)
        
        chroma_client = chromadb.Client()
        collection = chroma_client.get_or_create_collection(name="markdown_rag")

        embeddings = [self._get_embedding(chunk) for chunk in chunks]
        ids = [f"chunk_{i}" for i in range(len(chunks))]

        collection.add(
            documents=chunks,
            embeddings=embeddings,
            ids=ids
        )
        return collection

    def _build_langgraph(self):
        # 1. Reformulate incoming follow-ups into a standalone question for retrieval
        def contextualize_query_node(state: RAGState) -> dict:
            messages = state["messages"]
            if len(messages) <= 1:
                return {"standalone_query": messages[-1].content}

            system_prompt = (
                "Given a chat history and the latest user prompt which might reference context in the chat history, "
                "formulate a standalone question that can be understood without the chat history. "
                "Do NOT answer the question, just reformulate it if needed and otherwise return it as is."
            )
            
            prompt_messages = [SystemMessage(content=system_prompt)] + messages
            response = self.llm.invoke(prompt_messages)
            return {"standalone_query": response.content}

        # 2. Retrieve vectors based on the standalone query
        def retrieve_node(state: RAGState) -> dict:
            query = state["standalone_query"]
            query_embedding = self._get_embedding(query)
            
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=3
            )
            retrieved_docs = results["documents"][0] if results["documents"] else []
            return {"context": retrieved_docs}

        # 3. Generate answer using chat history and retrieved context
        def generate_node(state: RAGState) -> dict:
            context = "\n\n".join(state["context"])
            messages = state["messages"]
            
            system_instruction = SystemMessage(content=f"""You are a helpful assistant answering questions based on Building Regulations of Goa.
Do not mention that you are answering based on any provided document. Only if needed, ask a question to the client/user to understand their query better.

Context from Knowledge Base:
{context}""")

            # Feed full conversation history along with system context
            full_prompt = [system_instruction] + messages
            response = self.llm.invoke(full_prompt)
            
            return {"messages": [response]}

        # Build Graph
        workflow = StateGraph(RAGState)
        
        workflow.add_node("contextualize", contextualize_query_node)
        workflow.add_node("retrieve", retrieve_node)
        workflow.add_node("generate", generate_node)

        workflow.add_edge(START, "contextualize")
        workflow.add_edge("contextualize", "retrieve")
        workflow.add_edge("retrieve", "generate")
        workflow.add_edge("generate", END)

        # Compile with checkpointer memory enabled
        return workflow.compile(checkpointer=self.memory)

    def answer_query(self, query: str, session_id: str) -> dict:
        # LangGraph config uses thread_id to track separate sessions
        config = {"configurable": {"thread_id": session_id}}
        
        initial_state = {
            "messages": [HumanMessage(content=query)],
            "context": [],
            "standalone_query": ""
        }
        
        result = self.graph.invoke(initial_state, config=config)
        
        # Extract last AI message
        last_message = result["messages"][-1]
        
        return {
            "answer": str(last_message.content),
            "context": result.get("context", [])
        }
