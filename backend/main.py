import os
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from database import engine, Base, get_db
from models import Job, Node
from fuzzer_service import run_fuzzing_job_task

# Initialize Database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Learn Fuzz API",
    description="Backend API for running dynamic eval fuzzing campaigns on LLMs.",
    version="1.0.0"
)


# Enable CORS for frontend flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Schemas
class StartFuzzRequest(BaseModel):
    seed_prompt: str = Field(..., description="The initial query to begin fuzzing.")
    target_model: str = Field(..., description="The LLM model name being probed (e.g. gemini/gemini-1.5-pro, openai/gpt-4o-mini).")
    judge_model: str = Field("openai/gpt-4o-mini", description="The evaluator LLM (defaults to openai/gpt-4o-mini).")
    max_depth: int = Field(4, ge=1, le=5, description="Max depth of the fuzzing tree (1 to 5).")
    openai_api_key: Optional[str] = Field(None, description="OpenAI API Key.")
    anthropic_api_key: Optional[str] = Field(None, description="Anthropic API Key.")
    gemini_api_key: Optional[str] = Field(None, description="Gemini API Key.")
    azure_api_key: Optional[str] = Field(None, description="Azure API Key.")
    groq_api_key: Optional[str] = Field(None, description="Groq API Key.")
    openrouter_api_key: Optional[str] = Field(None, description="OpenRouter API Key.")

class JobResponse(BaseModel):
    job_id: str
    status: str
    seed_prompt: str
    target_model: str
    judge_model: str
    max_depth: int
    created_at: str

class NodeResponse(BaseModel):
    id: str
    job_id: str
    parent_id: Optional[str]
    prompt: str
    response: Optional[str]
    score: Optional[int]
    depth: int
    strategy: str
    reasoning: Optional[str]
    breaking_point: Optional[str]
    created_at: str

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    nodes_count: int
    max_depth_reached: int
    success_rate: float
    breaking_points_count: int
    breaking_points: List[str]


@app.get("/", tags=["General"])
def read_root():
    return {"message": "Welcome to the Learn Fuzz API. Access documentation at /docs."}



@app.post("/start-fuzz", response_model=dict, status_code=status.HTTP_201_CREATED, tags=["Fuzzing"])
def start_fuzz(
    request: StartFuzzRequest, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):
    """Starts a new LLM fuzzing job in the background."""
    # Build API keys dictionary
    api_keys = {
        "openai_api_key": request.openai_api_key or os.getenv("OPENAI_API_KEY"),
        "anthropic_api_key": request.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY"),
        "gemini_api_key": request.gemini_api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"),
        "azure_api_key": request.azure_api_key or os.getenv("AZURE_API_KEY"),
        "groq_api_key": request.groq_api_key or os.getenv("GROQ_API_KEY"),
        "openrouter_api_key": request.openrouter_api_key or os.getenv("OPENROUTER_API_KEY")
    }

    # Verify that at least one API key is present for target/judge models
    # We let LiteLLM complain if specific key is missing, but check if we have *something* or expect it in env
    
    # Create database entry
    job = Job(
        status="PENDING",
        seed_prompt=request.seed_prompt,
        target_model=request.target_model,
        judge_model=request.judge_model,
        max_depth=request.max_depth
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Queue background processing
    background_tasks.add_task(
        run_fuzzing_job_task,
        job_id=job.id,
        seed_prompt=request.seed_prompt,
        target_model=request.target_model,
        judge_model=request.judge_model,
        max_depth=request.max_depth,
        api_keys=api_keys
    )

    return {"job_id": job.id, "message": "Fuzzing job successfully initialized in background."}


@app.get("/jobs", response_model=List[JobResponse], tags=["Fuzzing"])
def get_jobs(db: Session = Depends(get_db)):
    """Retrieves all fuzzing jobs sorted by creation date."""
    jobs = db.query(Job).order_by(Job.created_at.desc()).all()
    return [
        JobResponse(
            job_id=j.id,
            status=j.status,
            seed_prompt=j.seed_prompt,
            target_model=j.target_model,
            judge_model=j.judge_model,
            max_depth=j.max_depth,
            created_at=j.created_at.isoformat()
        )
        for j in jobs
    ]


@app.get("/job/{job_id}/status", response_model=JobStatusResponse, tags=["Fuzzing"])
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """Returns progress statistics and status for a specific job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    nodes = db.query(Node).filter(Node.job_id == job_id).all()
    
    nodes_count = len(nodes)
    max_depth_reached = max([n.depth for n in nodes]) if nodes else 0
    
    # Calculate success rate (Score >= 8)
    passing_nodes = [n for n in nodes if n.score is not None and n.score >= 8]
    success_rate = (len(passing_nodes) / nodes_count) if nodes_count > 0 else 0.0
    
    # Gather breaking point summaries
    breaking_points = [n.breaking_point for n in nodes if n.breaking_point is not None]

    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        nodes_count=nodes_count,
        max_depth_reached=max_depth_reached,
        success_rate=round(success_rate, 2),
        breaking_points_count=len(breaking_points),
        breaking_points=breaking_points
    )


@app.get("/job/{job_id}/tree", response_model=List[NodeResponse], tags=["Fuzzing"])
def get_job_tree(job_id: str, db: Session = Depends(get_db)):
    """Returns all nodes belonging to a job, representing the tree structure."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    nodes = db.query(Node).filter(Node.job_id == job_id).order_by(Node.created_at.asc()).all()
    
    return [
        NodeResponse(
            id=n.id,
            job_id=n.job_id,
            parent_id=n.parent_id,
            prompt=n.prompt,
            response=n.response,
            score=n.score,
            depth=n.depth,
            strategy=n.strategy,
            reasoning=n.reasoning,
            breaking_point=n.breaking_point,
            created_at=n.created_at.isoformat()
        )
        for n in nodes
    ]


@app.delete("/job/{job_id}", tags=["Fuzzing"])
def delete_job(job_id: str, db: Session = Depends(get_db)):
    """Deletes a fuzzing job and its associated nodes."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    db.delete(job)
    db.commit()
    return {"message": f"Job {job_id} and all related nodes deleted successfully."}
