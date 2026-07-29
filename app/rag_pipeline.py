import os
from typing import TypedDict, List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
import chromadb
from google import genai  # Google GenAI SDK

# Define the State for LangGraph
class RAGState(TypedDict):
    query: str
    context: List[str]
    generation: str

class RAGPipeline:
    def __init__(self, file_path: str):
        self.file_path = file_path
        # Initialize Gemini GenAI client
        self.genai_client = genai.Client()
        self.llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite")
        
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
        with open(self.file_path, "r", encoding="utf-8") as f:
            markdown_content = f.read()

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            separators=["\n## ", "\n### ", "\n\n", "\n", " "]
        )

        chunks = text_splitter.split_text(markdown_content)
        
        # Create Chroma collection
        chroma_client = chromadb.Client()
        collection = chroma_client.get_or_create_collection(name="markdown_rag")

        embeddings = [self._get_embedding(chunk) for chunk in chunks]
        ids = [f"chunk_{i}" for i in range(len(chunks))]

        collection.add(
            documents=chunks,
            embeddings=embeddings,
            ids=ids
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
            
            prompt = f"""You are a helpful assistant answering questions based on Building Regulations of Goa.
            Do not mention that you are answering based on any provided document. Only if needed, ask a question to the client/user to understand their query better.
            Context:
            {context}
            
            Question: {query}
            Answer:"""
            
            response = self.llm.invoke(prompt)
            return {"generation": response.content}

        # Build Graph
        workflow = StateGraph(RAGState)
        workflow.add_node("retrieve", retrieve_node)
        workflow.add_node("generate", generate_node)

        workflow.add_edge(START, "retrieve")
        workflow.add_edge("retrieve", "generate")
        workflow.add_edge("generate", END)

        return workflow.compile()  # Must return the compiled graph!

    def answer_query(self, query: str) -> dict:
        initial_state = {"query": query, "context": [], "generation": ""}
        result = self.graph.invoke(initial_state)
        
        generation = result.get("generation")
        clean_answer = generation[0]["text"] if generation else "No answer generated."

        return {
            "answer": clean_answer,
            "context": result.get("context", [])
        }
