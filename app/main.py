from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.rag_pipeline import RAGPipeline

app = FastAPI(title="RAG QA API")

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    answer: str
    context: list
    is_exit: bool = False

rag_system = None

@app.on_event("startup")
def startup_event():
    global rag_system
    rag_system = RAGPipeline(file_path="knowledge_base.md")

@app.post("/chat", response_model=QueryResponse)
def chat_endpoint(request: QueryRequest):
    user_input = request.query.strip()
    
    if not user_input:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    
    # Check for exit commands
    if user_input.lower() in ["q", "quit", "exit"]:
        return QueryResponse(
            answer="Session ended. Thanks for chatting!",
            context=[],
            is_exit=True
        )
    
    # Run user query through the pre-loaded pipeline
    result = rag_system.answer_query(user_input)
    
    return QueryResponse(
        answer=result["answer"],
        context=result["context"],
        is_exit=False
    )
