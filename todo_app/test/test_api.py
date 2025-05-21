import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db
from app.core import security

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def test_db():
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()
    
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(test_db):
    def override_get_db():
        try:
            yield test_db
        finally:
            test_db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides = {}

def test_create_user(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data

def test_login(client, test_db):
    hashed_password = security.get_password_hash("password123")
    from app.models.user import User

    user = User(email="test@example.com", hashed_password=hashed_password)
    test_db.add(user)
    test_db.commit()

    response = client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "password123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_create_todo(client, test_db):
    hashed_password = security.get_password_hash("password123")
    from app.models.user import User
    
    user = User(email="test@example.com", hashed_password=hashed_password)
    test_db.add(user)
    test_db.commit()

    response = client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "password123"},
    )
    token = response.json()["access_token"]

    response = client.post(
        "/api/v1/todos",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Test Todo", "description": "This is a test todo"}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Todo"
    assert data["description"] == "This is a test todo"
    assert data["completed"] is False
    assert "id" in data
    assert "created_at" in data
    assert data["owner_id"] == user.id

def test_get_todos(client, test_db):
    hashed_password = security.get_password_hash("password123")
    from app.models.user import User
    from app.models.todo import Todo

    user = User(email="test@example.com", hashed_password=hashed_password)
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    todo1 = Todo(title="Todo 1", description="First todo", owner_id=user.id)
    todo2 = Todo(title="Todo 2", description="Second todo", owner_id=user.id)
    test_db.add(todo1)
    test_db.add(todo2)
    test_db.commit()


    response = client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "password123"},
    )
    token = response.json()["access_token"]

    response = client.post(
        "/api/v1/todos",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["title"] == "Todo 1"
    assert data[1]["title"] == "Todo 2"

def test_update_todo(client, test_db):
    hashed_password = security.get_password_hash("password123")
    from app.models.user import User
    from app.models.todo import Todo

    user = User(email="test@example.com", hashed_password=hashed_password)
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    todo = Todo(title="Old Title", description="Old Description", owner_id=user.id)
    test_db.add(todo)
    test_db.commit()
    test_db.refresh(todo)

    response = client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "password123"},
    )
    token = response.json()["access_token"]

    response = client.put(
        f"/api/v1/todos/{todo.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "New Title", "description": "New Description", "completed": True}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "New Title"
    assert data["description"] == "New Description"
    assert data["completed"] is True

def test_delete_todo(client, test_db):
    hashed_password = security.get_password_hash("password123")
    from app.models.user import User
    from app.models.todo import Todo

    user = User(email="test@example.com", hashed_password=hashed_password)
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    todo = Todo(title="Test Todo", description="TO be deleted", owner_id=user.id)
    test_db.add(todo)
    test_db.commit()
    test_db.refresh(todo)

    response = client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "password123"},
    )
    token = response.json()["access_token"]

    response = client.delete(
        f"/api/v1/todos/{todo.id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 204

    response = client.get(
        f"/api/v1/todos/{todo.id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404