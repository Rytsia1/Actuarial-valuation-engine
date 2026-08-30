import uuid
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum

class NodeType(str, Enum):
    INPUT = "input"
    PREMIUM = "premium"
    EXPENSE = "expense"
    MORTALITY = "mortality"
    SURVIVAL = "survival"
    BENEFIT = "benefit"
    CASHFLOW = "cashflow"
    DISCOUNT = "discount"
    OUTPUT = "output"

class Node(BaseModel):
    id: str = Field(..., description="Unique UUID or slug")
    type: NodeType
    config: Dict[str, Any] = Field(default_factory=dict, description="Configuration parameters for the node")
    position: Optional[Dict[str, float]] = Field(default=None, description="Visual position for UI, ignored by engine")

class Edge(BaseModel):
    id: str
    source: str = Field(..., description="Source Node ID")
    target: str = Field(..., description="Target Node ID")
    source_handle: Optional[str] = Field(None, description="Output port name, e.g., 'qx'")
    target_handle: Optional[str] = Field(None, description="Input port name, e.g., 'mortality'")

class Blueprint(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Untitled Projection"
    nodes: List[Node]
    edges: List[Edge]
