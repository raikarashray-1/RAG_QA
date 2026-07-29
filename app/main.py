from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from app.rag_pipeline import RAGPipeline

app = FastAPI(title="RAG QA API")

class QueryRequest(BaseModel):
    query: str
    session_id: str = Field(default="default_session", description="Unique session ID per user/conversation")

class QueryResponse(BaseModel):
    answer: str
    context: list
    session_id: str
    is_exit: bool = False

rag_system = None

@app.on_event("startup")
def startup_event():
    global rag_system
    rag_system = RAGPipeline(file_path="knowledge_base.md")

@app.post("/chat", response_model=QueryResponse)
def chat_endpoint(request: QueryRequest):
    user_input = request.query.strip()
    session_id = request.session_id.strip() or "default_session"
    
    if not user_input:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    
    # Check for exit commands
    if user_input.lower() in ["q", "quit", "exit"]:
        return QueryResponse(
            answer="Session ended. Thanks for chatting!",
            context=[],
            session_id=session_id,
            is_exit=True
        )
    
    try:
        # Pass both query and session_id to the pipeline
        result = rag_system.answer_query(query=user_input, session_id=session_id)
        
        raw_context = result.get("context", [])
        formatted_context = []
        for item in raw_context:
            if isinstance(item, str):
                formatted_context.append(item)
            elif hasattr(item, "page_content"):
                formatted_context.append(str(item.page_content))
            else:
                formatted_context.append(str(item))

        return QueryResponse(
            answer=result.get("answer", "No answer generated."),
            context=formatted_context,
            session_id=session_id,
            is_exit=False
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")

@app.get("/")
def read_root():
    return {"status": "ok"}
