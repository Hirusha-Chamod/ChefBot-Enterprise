from pydantic import BaseModel, EmailStr
from typing import Optional, List

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    dietary_profile: Optional[str] = 'Standard'

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    dietary_profile: Optional[str] = 'Standard'

class Token(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    user: UserResponse

class ChatRequest(BaseModel):
    prompt: str
    allow_web_search: bool = True
    dietary_profile: Optional[str] = 'Standard'
    thread_id: str = 'default_session'
    servings: int = 2

class ChatResponse(BaseModel):
    recipe: str
    thread_id: str
    dietary_applied: str
    servings_applied: int = 2

class SessionResponse(BaseModel):
    id: int
    thread_id: str
    user_id: Optional[int] = None
    title: str
    created_at: str
    updated_at: str

class MessageItem(BaseModel):
    role: str
    content: str

class HistoryResponse(BaseModel):
    thread_id: str
    messages: List[MessageItem]
