# agent/states.py
from typing import List, Optional
from pydantic import BaseModel

class PlanFile(BaseModel):
    path: str
    purpose: str

class Plan(BaseModel):
    name: str
    description: str
    techstack: str
    features: List[str]
    files: List[PlanFile]

class TaskStep(BaseModel):
    # ✅ IMPORTANT: no underscore
    filepath: str
    task_description: str
    current_file_content: Optional[str] = None

class TaskPlan(BaseModel):
    implementation_steps: List[TaskStep]
    plan: Optional[Plan] = None

class CoderState(BaseModel):
    task_plan: TaskPlan
    current_step_idx: int = 0
