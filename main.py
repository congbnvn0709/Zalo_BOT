"""
Main Application Entrypoint for Zalo Attendance System (Milestone 3).
Serves the FastAPI REST API and mounts the Single Page Application (SPA).
"""

import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router as api_router

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
STATIC_DIR = os.path.join(PROJECT_ROOT, "static")

app = FastAPI(
    title="Zalo Attendance Bot",
    description="Hệ thống chấm công Zalo tự động & Xuất Excel",
    version="1.0.0",
)

# Enable CORS for local cross-origin development if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include REST API routes at /api
app.include_router(api_router, prefix="/api")

# Mount static asset directory
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=FileResponse)
def serve_index():
    """Serves the main interactive dashboard SPA."""
    index_file = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(index_file):
        return FileResponse(os.path.join(PROJECT_ROOT, "PROJECT.md"), media_type="text/plain")
    return FileResponse(index_file, media_type="text/html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
