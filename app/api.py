import logging
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.scheduler import run_pipeline

app = FastAPI(
    title="Production Planning API",
    version="0.1.0",
    docs_url="/",          
)

class OptimizeRequest(BaseModel):
    llm_input: str

@app.post("/optimize", response_model=Dict[str, Any])
def optimize(req: OptimizeRequest):
    try:
        return run_pipeline(req.llm_input)
    except Exception as exc:
        logging.exception("run_pipeline 出错")
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
