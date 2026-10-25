"""
Root entrypoint for HCM Lite FastAPI backend.
Allows running:
  - uvicorn main:app --reload --port 5000
  - python main.py
  - uvicorn app.main:app --reload --port 5000
  - python run.py
"""
import uvicorn
from app.main import app
from app.core.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )
