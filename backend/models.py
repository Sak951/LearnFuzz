import datetime
import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=generate_uuid)
    status = Column(String, default="PENDING")  # PENDING, RUNNING, COMPLETED, FAILED
    seed_prompt = Column(String, nullable=False)
    target_model = Column(String, nullable=False)
    judge_model = Column(String, nullable=False)
    max_depth = Column(Integer, default=5)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    nodes = relationship("Node", back_populates="job", cascade="all, delete-orphan")


class Node(Base):
    __tablename__ = "nodes"

    id = Column(String, primary_key=True, default=generate_uuid)
    job_id = Column(String, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    parent_id = Column(String, ForeignKey("nodes.id", ondelete="CASCADE"), nullable=True)
    
    prompt = Column(String, nullable=False)
    response = Column(String, nullable=True)
    score = Column(Integer, nullable=True)  # 1-10 scale
    depth = Column(Integer, default=0)
    strategy = Column(String, nullable=False)  # seed, red_herrings, constraints, chain_sequence, simplify
    reasoning = Column(String, nullable=True)  # Judge model's reasoning
    breaking_point = Column(String, nullable=True)  # Breaking point description if applicable
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    job = relationship("Job", back_populates="nodes")
    parent = relationship("Node", remote_side=[id], back_populates="children")
    children = relationship("Node", back_populates="parent", cascade="all, delete-orphan")
