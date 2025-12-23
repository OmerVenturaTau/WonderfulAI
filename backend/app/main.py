import json
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .agents import stream_agent
from .tools import get_tool_stats

app = FastAPI(title="Wonderful Pharmacy Agent")

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend files only if not using Docker (nginx handles it in Docker)
SERVE_FRONTEND = os.getenv("SERVE_FRONTEND", "false").lower() == "true"
if SERVE_FRONTEND:
    FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
    
    @app.get("/")
    def index():
        return FileResponse(FRONTEND_DIR / "index.html")

@app.post("/api/chat/stream")
async def chat_stream(req: Request):
    payload = await req.json()
    messages = payload.get("messages", [])

    def sse():
        for ev in stream_agent(messages):
            yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"

    return StreamingResponse(sse(), media_type="text/event-stream")


@app.get("/api/tools/stats")
def tools_stats():
    """
    Return aggregated tool usage statistics for frontend visualization.
    """
    stats = get_tool_stats()
    return JSONResponse({"tools": stats})
