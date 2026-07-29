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
    
    try:
        # Run user query through the pre-loaded pipeline
        result = rag_system.answer_query(user_input)
        
        # Ensure context is formatted safely as a list of strings
        raw_context = result.get("context", [])
        formatted_context = []
        for item in raw_context:
            if isinstance(item, str):
                formatted_context.append(item)
            elif hasattr(item, "page_content"):  # LangChain Document
                formatted_context.append(str(item.page_content))
            else:
                formatted_context.append(str(item))

        return QueryResponse(
            answer=str(result.get("answer", "No answer generated.")),
            context=formatted_context,
            is_exit=False
        )
        
    except Exception as e:
        # Prevent 500 crash pages by returning a clean error payload
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")
# app/main.py

@app.get("/")
def read_root():
    return {"status": "ok"}
