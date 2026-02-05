from fastapi import FastAPI, HTTPException, Depends, status, Header, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session as DBSession
from typing import List, Optional
import os
import sys
from datetime import datetime, timedelta

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine, Base, get_db
from models.quiz import Quiz, QuizSubmission
from models.user import User, Session
from schemas import (
    QuizResponse, QuizCreate, QuizListItem, WikipediaURL, 
    QuizSubmissionCreate, QuizSubmissionResponse,
    UserSignup, UserLogin, UserResponse, AuthResponse, GuestLoginResponse
)
from services.scraper import WikipediaScraper
from services.llm_service import QuizGenerator

# Create database tables (schema is now fixed in Neon PostgreSQL)
Base.metadata.create_all(bind=engine)
print("✅ Database connected successfully!")


app = FastAPI(
    title="Wiki Quiz Generator API",
    description="Generate quizzes from Wikipedia articles using AI",
    version="1.0.0"
)

# Enable GZip compression for responses (reduces payload size by ~70%)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
scraper = WikipediaScraper()
quiz_generator = QuizGenerator()


# ============== Authentication Helper ==============

def get_current_user(authorization: Optional[str] = Header(None), db: DBSession = Depends(get_db)) -> Optional[User]:
    """Get current user from Authorization header token"""
    if not authorization:
        return None
    
    try:
        # Extract token from "Bearer <token>" format
        if authorization.startswith("Bearer "):
            token = authorization[7:]
        else:
            token = authorization
        
        # Find session by token
        session = db.query(Session).filter(Session.token == token).first()
        if not session:
            return None
        
        # Check if session is expired
        if session.expires_at < datetime.utcnow():
            db.delete(session)
            db.commit()
            return None
        
        # Get user
        user = db.query(User).filter(User.id == session.user_id).first()
        return user
    except Exception:
        return None


# ============== Authentication Endpoints ==============

@app.post("/api/auth/signup", response_model=AuthResponse)
async def signup(user_data: UserSignup, db: DBSession = Depends(get_db)):
    """Register a new user"""
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    new_user = User(
        email=user_data.email,
        password_hash=User.hash_password(user_data.password),
        name=user_data.name,
        is_guest=False
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Create session
    token = Session.generate_token()
    new_session = Session(
        user_id=new_user.id,
        token=token,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(new_session)
    db.commit()
    
    return {
        "user": new_user.to_dict(),
        "token": token,
        "message": "Account created successfully"
    }


@app.post("/api/auth/login", response_model=AuthResponse)
async def login(user_data: UserLogin, db: DBSession = Depends(get_db)):
    """Login with email and password"""
    user = db.query(User).filter(User.email == user_data.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not user.verify_password(user_data.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Update last login
    user.last_login = datetime.utcnow()
    
    # Create session
    token = Session.generate_token()
    new_session = Session(
        user_id=user.id,
        token=token,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(new_session)
    db.commit()
    
    return {
        "user": user.to_dict(),
        "token": token,
        "message": "Login successful"
    }


@app.post("/api/auth/guest", response_model=GuestLoginResponse)
async def guest_login(db: DBSession = Depends(get_db)):
    """Create a guest account for temporary access"""
    # Generate guest credentials
    guest_creds = User.generate_guest_credentials()
    
    # Create guest user
    guest_user = User(
        email=guest_creds["email"],
        password_hash=User.hash_password(guest_creds["password"]),
        name=guest_creds["name"],
        is_guest=True
    )
    db.add(guest_user)
    db.commit()
    db.refresh(guest_user)
    
    # Create session (shorter expiry for guests - 24 hours)
    token = Session.generate_token()
    new_session = Session(
        user_id=guest_user.id,
        token=token,
        expires_at=datetime.utcnow() + timedelta(hours=24)
    )
    db.add(new_session)
    db.commit()
    
    return {
        "user": guest_user.to_dict(),
        "token": token,
        "message": "Guest session created",
        "is_guest": True
    }


@app.post("/api/auth/logout")
async def logout(authorization: Optional[str] = Header(None), db: DBSession = Depends(get_db)):
    """Logout and invalidate session"""
    if authorization:
        token = authorization[7:] if authorization.startswith("Bearer ") else authorization
        session = db.query(Session).filter(Session.token == token).first()
        if session:
            db.delete(session)
            db.commit()
    
    return {"message": "Logged out successfully"}


@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: Optional[User] = Depends(get_current_user)):
    """Get current logged in user info"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return current_user.to_dict()


@app.get("/")
async def root(response: Response):
    response.headers["Cache-Control"] = "public, max-age=3600"
    return {"message": "Wiki Quiz Generator API", "docs": "/docs"}

@app.post("/api/generate-quiz", response_model=QuizResponse, status_code=status.HTTP_201_CREATED)
async def generate_quiz(
    quiz_data: QuizCreate, 
    db: DBSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Generate a quiz from a Wikipedia URL.
    Scrapes the article, generates FRESH quiz using LLM, and stores in database.
    NOTE: Always generates NEW questions - no caching for unique quiz experience each session.
    """
    url = str(quiz_data.url)
    
    # CHANGED: No longer returning cached quizzes - always generate fresh questions
    # This ensures that every session gets NEW questions as per requirements
    print(f"🎲 Generating FRESH quiz for: {url}")
    
    try:
        # Scrape Wikipedia article
        article_data = scraper.scrape_article(url)
        
        # Performance Upgrade: Generate quiz questions and related topics IN PARALLEL
        # This cuts LLM wait time by half!
        import asyncio
        quiz_task = quiz_generator.generate_quiz(article_data['full_text'], article_data['title'])
        topics_task = quiz_generator.generate_related_topics(article_data['full_text'], article_data['title'])
        
        # Run both tasks simultaneously
        quiz_questions, related_topics = await asyncio.gather(quiz_task, topics_task)
        
        # Create quiz record with optional user_id
        new_quiz = Quiz(
            url=url,
            user_id=current_user.id if current_user else None,
            title=article_data['title'],
            summary=article_data['summary'],
            key_entities=article_data['key_entities'],
            sections=article_data['sections'],
            raw_html=article_data['raw_html'],
            quiz_data=quiz_questions,
            related_topics=related_topics
        )
        
        db.add(new_quiz)
        db.commit()
        db.refresh(new_quiz)
        
        print(f"✅ Successfully generated quiz with {len(quiz_questions)} questions!")
        
        return new_quiz.to_dict()
        
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating quiz: {str(e)}")

@app.get("/api/quizzes", response_model=List[QuizListItem])
async def get_quizzes(
    skip: int = 0, 
    limit: int = 100, 
    db: DBSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
    response: Response = None
):
    """Get list of all generated quizzes (history) - filtered by user if logged in"""
    from sqlalchemy import or_
    
    # Add cache headers for quiz list (short cache as data changes frequently)
    if response:
        response.headers["Cache-Control"] = "private, max-age=60"
    
    if current_user:
        # Return user's quizzes PLUS public quizzes (where user_id is null)
        # This ensures new users can still see existing public quizzes
        quizzes = db.query(Quiz).filter(
            or_(Quiz.user_id == current_user.id, Quiz.user_id == None)
        ).order_by(Quiz.created_at.desc()).offset(skip).limit(limit).all()
    else:
        # Not logged in - show all quizzes
        quizzes = db.query(Quiz).order_by(Quiz.created_at.desc()).offset(skip).limit(limit).all()
    
    return [quiz.to_dict() for quiz in quizzes]

@app.get("/api/quizzes/{quiz_id}", response_model=QuizResponse)
async def get_quiz(quiz_id: int, db: DBSession = Depends(get_db), response: Response = None):
    """Get a specific quiz by ID"""
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    # Cache quiz data for 5 minutes (quizzes don't change)
    if response:
        response.headers["Cache-Control"] = "public, max-age=300"
    
    return quiz.to_dict()

@app.delete("/api/quizzes/{quiz_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quiz(quiz_id: int, db: DBSession = Depends(get_db)):
    """Delete a quiz by ID"""
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    db.delete(quiz)
    db.commit()
    return {"message": "Quiz deleted successfully"}

@app.get("/api/validate-url")
async def validate_url(url: str):
    """Validate if URL is a valid Wikipedia URL"""
    is_valid = scraper.validate_url(url)
    return {"valid": is_valid, "url": url}

@app.get("/api/health")
async def health_check(response: Response):
    """Health check endpoint"""
    response.headers["Cache-Control"] = "public, max-age=10"
    return {"status": "healthy", "service": "Wiki Quiz Generator"}

@app.post("/api/quizzes/{quiz_id}/submit", response_model=QuizSubmissionResponse)
async def submit_quiz(
    quiz_id: int, 
    submission: QuizSubmissionCreate, 
    db: DBSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Submit quiz answers and get results.
    Calculates score, stores submission, and returns correct answers with explanations.
    """
    # Get the quiz
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    quiz_data = quiz.quiz_data
    user_answers = submission.user_answers
    
    # Validate submission
    if len(user_answers) != len(quiz_data):
        raise HTTPException(
            status_code=400, 
            detail=f"Expected {len(quiz_data)} answers, got {len(user_answers)}"
        )
    
    # Calculate score
    correct_count = 0
    correct_answers = []
    explanations = []
    
    for i, (question, user_answer) in enumerate(zip(quiz_data, user_answers)):
        correct_answer = question['answer']
        correct_answers.append(correct_answer)
        explanations.append(question.get('explanation', 'No explanation provided'))
        
        if user_answer == correct_answer:
            correct_count += 1
    
    total_questions = len(quiz_data)
    percentage = (correct_count / total_questions) * 100 if total_questions > 0 else 0
    
    # Store submission in database with optional user_id
    new_submission = QuizSubmission(
        quiz_id=quiz_id,
        user_id=current_user.id if current_user else None,
        user_answers=user_answers,
        score=correct_count,
        total_questions=total_questions,
        percentage=percentage
    )
    
    db.add(new_submission)
    db.commit()
    db.refresh(new_submission)
    
    # Return results with correct answers and explanations
    return {
        "id": new_submission.id,
        "quiz_id": quiz_id,
        "user_answers": user_answers,
        "score": correct_count,
        "total_questions": total_questions,
        "percentage": percentage,
        "submitted_at": new_submission.submitted_at.isoformat() if new_submission.submitted_at else None,
        "correct_answers": correct_answers,
        "explanations": explanations
    }

@app.get("/api/quizzes/{quiz_id}/submissions")
async def get_quiz_submissions(
    quiz_id: int, 
    db: DBSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get all submissions for a specific quiz"""
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    if current_user:
        # Return only this user's submissions
        submissions = db.query(QuizSubmission).filter(
            QuizSubmission.quiz_id == quiz_id,
            QuizSubmission.user_id == current_user.id
        ).order_by(QuizSubmission.submitted_at.desc()).all()
    else:
        # Return all submissions for the quiz
        submissions = db.query(QuizSubmission).filter(QuizSubmission.quiz_id == quiz_id).order_by(QuizSubmission.submitted_at.desc()).all()
    return [sub.to_dict() for sub in submissions]

@app.get("/api/me/submissions")
async def get_my_submissions(
    db: DBSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get all submissions for the current user across all quizzes"""
    if not current_user:
        return []
    
    submissions = db.query(QuizSubmission).filter(
        QuizSubmission.user_id == current_user.id
    ).order_by(QuizSubmission.submitted_at.desc()).all()
    
    results = []
    for sub in submissions:
        quiz = db.query(Quiz).filter(Quiz.id == sub.quiz_id).first()
        results.append({
            "id": sub.id,
            "quiz_id": sub.quiz_id,
            "quiz_title": quiz.title if quiz else "Deleted Quiz",
            "score": sub.score,
            "total_questions": sub.total_questions,
            "percentage": sub.percentage,
            "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None
        })
    
    return results

# Serve frontend static files
if os.path.exists("../frontend"):
    app.mount("/static", StaticFiles(directory="../frontend"), name="static")

@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """Serve frontend HTML"""
    frontend_path = os.path.join(os.path.dirname(__file__), "../frontend/index.html")
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    raise HTTPException(status_code=404, detail="Frontend not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)