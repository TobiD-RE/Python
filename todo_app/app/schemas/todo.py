from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class TodoBase(BaseModel):
    title: str
    description: Optional[str] = None

class ToDoCreate(TodoBase):
    pass

class TodoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None

class TodoInDBBase(TodoBase):
    id: int
    completed: bool
    created_at: datetime
    owner_id: int

    class Config:
        orm_mode = True

class Todo(TodoInDBBase):
    pass