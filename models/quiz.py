from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, Float
from sqlalchemy.sql import func
from database import Base

class Quiz(Base):
    __tablename__ = "quizzes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Optional for guest users
    url = Column(String(500), nullable=False)
    title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=True)
    key_entities = Column(JSON, nullable=True)
    sections = Column(JSON, nullable=True)
    raw_html = Column(Text, nullable=True)
    quiz_data = Column(JSON, nullable=False)
    related_topics = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "url": self.url,
            "title": self.title,
            "summary": self.summary,
            "key_entities": self.key_entities,
            "sections": self.sections,
            "quiz": self.quiz_data,
            "related_topics": self.related_topics,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class QuizSubmission(Base):
    __tablename__ = "quiz_submissions"
    
    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Optional for guest users
    user_answers = Column(JSON, nullable=False)  # Store user's selected answers
    score = Column(Integer, nullable=False)  # Number of correct answers
    total_questions = Column(Integer, nullable=False)  # Total questions (5)
    percentage = Column(Float, nullable=False)  # Score percentage
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def to_dict(self):
        return {
            "id": self.id,
            "quiz_id": self.quiz_id,
            "user_id": self.user_id,
            "user_answers": self.user_answers,
            "score": self.score,
            "total_questions": self.total_questions,
            "percentage": round(self.percentage, 1),
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None
        }