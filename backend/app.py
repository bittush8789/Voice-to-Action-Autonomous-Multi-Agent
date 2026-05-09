import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any

# Services & Orchestrator
from backend.services.groq_service import groq_service
from backend.services.db_service import get_workflow_history
from backend.memory.chroma_service import memory_service
from backend.agents.autogen_agent import autogen_service
from backend.workflows.orchestrator import app_workflow

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Voice-to-Action Autonomous Multi-Agent AI Assistant",
    description="Sleek, next-generation AI assistant that converts voice commands into automated actions.",
    version="1.0.0"
)

# Enable CORS for cross-origin frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request bodies
class ExecuteRequest(BaseModel):
    text: str
    audio_path: Optional[str] = None

class StoreMemoryRequest(BaseModel):
    command: str
    summary: str
    tool: str
    parameters: dict
    plan: list

class SearchMemoryRequest(BaseModel):
    query: str
    limit: Optional[int] = 2

# Ensure temporary upload directory exists
TEMP_DIR = os.path.join(os.path.dirname(__file__), "temp_uploads")
os.makedirs(TEMP_DIR, exist_ok=True)

# --------------------------------------------------------------------------
# API Routes
# --------------------------------------------------------------------------

@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    """Accepts an audio file upload and returns the Whisper transcript."""
    logger.info(f"Received audio transcription request: {file.filename}")
    
    # Save file locally inside workspace
    temp_file_path = os.path.join(TEMP_DIR, file.filename)
    try:
        with open(temp_file_path, "wb") as buffer:
            buffer.write(await file.read())
            
        transcript = groq_service.transcribe_audio(temp_file_path)
        
        # Clean up local temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            
        return {"status": "success", "transcript": transcript}
    except Exception as e:
        logger.error(f"Error during audio transcription: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/execute")
async def execute(payload: ExecuteRequest):
    """Executes the complete multi-agent LangGraph workflow and retrieves AutoGen collaboration."""
    logger.info(f"Executing workflow for: '{payload.text}'")
    
    try:
        # 1. Initialize LangGraph State
        initial_state = {
            "audio_path": payload.audio_path or "",
            "text_input": payload.text,
            "transcript": "",
            "intent": "",
            "parameters": {},
            "plan": [],
            "memory_context": [],
            "tool_output": {},
            "summary": "",
            "logs": []
        }
        
        # 2. Run LangGraph StateGraph Execution Pipeline
        final_state = app_workflow.invoke(initial_state)
        
        # 3. Perform AutoGen Group Chat collaboration for the corresponding command
        autogen_result = autogen_service.run_group_chat_collaboration(final_state["transcript"])
        
        return {
            "status": "success",
            "transcript": final_state["transcript"],
            "intent": final_state["intent"],
            "parameters": final_state["parameters"],
            "plan": final_state["plan"],
            "memory_context": final_state["memory_context"],
            "tool_output": final_state["tool_output"],
            "summary": final_state["summary"],
            "logs": final_state["logs"],
            "autogen": autogen_result
        }
    except Exception as e:
        logger.error(f"Error during workflow execution: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/memory/store")
async def store_memory(payload: StoreMemoryRequest):
    """Manually saves a semantic memory to ChromaDB."""
    logger.info(f"Manually saving memory: '{payload.command}'")
    try:
        memory_service.store_memory(
            user_command=payload.command,
            summary=payload.summary,
            workflow_plan=payload.plan,
            tool=payload.tool,
            parameters=payload.parameters
        )
        return {"status": "success", "message": "Memory stored successfully."}
    except Exception as e:
        logger.error(f"Error storing memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/memory/search")
async def search_memory(payload: SearchMemoryRequest):
    """Queries semantic memory from ChromaDB."""
    logger.info(f"Searching memory for: '{payload.query}'")
    try:
        results = memory_service.search_memory(payload.query, limit=payload.limit)
        return {"status": "success", "results": results}
    except Exception as e:
        logger.error(f"Error searching memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history")
async def get_history(limit: int = 50):
    """Retrieves SQLite workflow run logs."""
    logger.info("Retrieving workflow histories from SQLite DB.")
    try:
        history = get_workflow_history(limit=limit)
        return {"status": "success", "history": history}
    except Exception as e:
        logger.error(f"Error retrieving history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Liveness and readiness check endpoint."""
    return {"status": "healthy", "service": "Voice-to-Action API"}

# --------------------------------------------------------------------------
# Frontend static files mounting and rendering
# --------------------------------------------------------------------------

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

@app.get("/")
async def read_index():
    """Serves the dashboard home page."""
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Welcome to Voice-to-Action Multi-Agent AI Assistant! Frontend directory is being configured."}

# Mount static files (style.css, script.js, etc.)
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
