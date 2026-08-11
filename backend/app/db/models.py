from pydantic import BaseModel, EmailStr
from typing import Optional, List

# User Auth Schemas
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    dietary_profile: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# Chat Schemas
class ChatRequest(BaseModel):
    prompt: str
    allow_web_search: bool = True
    dietary_profile: Optional[str] = "Standard"  # Standard, Vegan, Keto, Gluten-Free, Nut-Free
    thread_id: Optional[str] = "default_session"

class ChatResponse(BaseModel):
    recipe: str
    thread_id: str
    dietary_applied: str
