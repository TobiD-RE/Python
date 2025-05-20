from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import models, schemas
from app.api import deps
from app.database import get_db

router = APIRouter()

@router.get("/", response_model=List[schemas.Todo])
def read_todos(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int =100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """Retrieve todos for current user"""
    todos = (
        db.query(models.Todo)
        .filter(models.Todo.owner_id == current_user.id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return todos

@router.post("/", response_model=schemas.Todo, status_code=status.HTTP_201_CREATED)
def create_todo(
    *,
    db: Session = Depends(get_db),
    todo_in: schemas.ToDoCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """Create todo"""
    todo = models.Todo(**todo_in.model_dump(), owner_id=current_user.id)
    db.add(todo)
    db.commit()
    db.refresh(todo)
    return todo

@router.get("/{todo_id}", response_model=schemas.Todo)
def read_todo(
    *,
    db: Session = Depends(get_db),
    todo_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """get todo by id"""
    todo = db.query(models.Todo).filter(models.Todo.id == todo_id, models.Todo.owner_id == current_user.id).first()
    if not todo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")
    
    return todo

@router.put("/{todo_id}", response_model=schemas.Todo)
def update_todo(
    *,
    db: Session = Depends(get_db),
    todo_id: int,
    todo_in: schemas.TodoUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """update todo"""
    todo = db.query(models.Todo).filter(models.Todo.id, models.Todo.owner_id == current_user.id).first()
    if not todo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")
    
    update_data = todo_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(todo, field, value)

    db.add(todo)
    db.commit()
    db.refresh(todo)
    return todo

@router.delete("/{todo_id}", response_model=schemas.Todo)
def delete_todo(
    *,
    db: Session = Depends(get_db),
    todo_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    todo = db.query(models.Todo).filter(models.Todo.id, models.Todo.owner_id == current_user.id).first()
    if not todo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")
    
    db.delete(todo)
    db.commit()
    return None

@router.patch("/{todo_id}/toggle", response_model=schemas.Todo)
def toggle_todo_completed(
    *,
    db: Session = Depends(get_db),
    todo_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """Toggle todo completed status"""
    todo = db.query(models.Todo).filter(models.Todo.id, models.Todo.owner_id == current_user.id).first()
    if not todo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")
    
    todo.completed = not todo.completed

    db.add(todo)
    db.commit()
    db.refresh(todo)
    return todo