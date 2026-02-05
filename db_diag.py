from database import engine
from sqlalchemy import text

def check():
    with engine.connect() as conn:
        print("--- Database Structure Check ---")
        
        # 1. List Tables
        tables = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")).fetchall()
        print(f"Tables found: {[t[0] for t in tables]}")
        
        # 2. Check Quizzes
        q_count = conn.execute(text("SELECT COUNT(*) FROM quizzes")).scalar()
        q_with_user = conn.execute(text("SELECT COUNT(*) FROM quizzes WHERE user_id IS NOT NULL")).scalar()
        print(f"Total Quizzes: {q_count}")
        print(f"Quizzes with User ID: {q_with_user}")
        
        # 3. Check Submissions
        if 'quiz_submissions' in [t[0] for t in tables]:
            s_count = conn.execute(text("SELECT COUNT(*) FROM quiz_submissions")).scalar()
            print(f"Total Submissions: {s_count}")
        else:
            print("ALERT: quiz_submissions table is MISSING!")
            
        # 4. Check Users
        u_count = conn.execute(text("SELECT COUNT(*) FROM users")).scalar()
        print(f"Total Users: {u_count}")
        
        # 5. Check Sessions
        if 'sessions' in [t[0] for t in tables]:
            sess_count = conn.execute(text("SELECT COUNT(*) FROM sessions")).scalar()
            print(f"Total Active Sessions: {sess_count}")
        else:
            print("ALERT: sessions table is MISSING!")

if __name__ == "__main__":
    try:
        check()
    except Exception as e:
        print(f"Error: {e}")
