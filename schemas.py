from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict, Any
from datetime import datetime

class QuizQuestion(BaseModel):
    question: str
    options: List[str]
    answer: str
    difficulty: str
    explanation: str

class QuizResponse(BaseModel):
    id: int
    url: str
    title: str
    summary: str
    key_entities: Dict[str, List[str]]
    sections: List[str]
    quiz: List[QuizQuestion]
    related_topics: List[str]
    created_at: Optional[str] = None
    
    class Config:
        from_attributes = True

class QuizCreate(BaseModel):
    url: str

class QuizListItem(BaseModel):
    id: int
    url: str
    title: str
    created_at: Optional[str] = None
    
    class Config:
        from_attributes = True

class WikipediaURL(BaseModel):
    url: HttpUrl

class QuizSubmissionCreate(BaseModel):
    quiz_id: int
    user_answers: List[str]  # List of selected answers for each question

class QuizSubmissionResponse(BaseModel):
    id: int
    quiz_id: int
    user_answers: List[str]
    score: int
    total_questions: int
    percentage: float
    submitted_at: Optional[str] = None
    correct_answers: List[str]  # Include correct answers for review
    explanations: List[str]  # Include explanations for each question
    
    class Config:
        from_attributes = True


# ============== Authentication Schemas ==============

class UserSignup(BaseModel):
    email: str
    password: str
    name: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    is_guest: bool
    created_at: Optional[str] = None
    
    class Config:
        from_attributes = True

class AuthResponse(BaseModel):
    user: UserResponse
    token: str
    message: str

class GuestLoginResponse(BaseModel):
    user: UserResponse
    token: str
    message: str
    is_guest: bool = True