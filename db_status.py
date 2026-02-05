from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    # Get all tables
    result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
    tables = [row[0] for row in result]
    print('All tables:', tables)
    
    # Check for submissions and sessions
    if 'quiz_submissions' in tables:
        result2 = conn.execute(text('SELECT COUNT(*) FROM quiz_submissions'))
        print('Submissions count:', result2.scalar())
    else:
        print('quiz_submissions table NOT FOUND')
    
    if 'sessions' in tables:
        result3 = conn.execute(text('SELECT COUNT(*) FROM sessions'))
        print('Sessions count:', result3.scalar())
    else:
        print('sessions table NOT FOUND')
    
    # Show sample data from each table
    if 'quizzes' in tables:
        print('\n=== Sample Quiz ===')
        result4 = conn.execute(text('SELECT id, title, user_id FROM quizzes LIMIT 1'))
        for row in result4:
            print(f'  ID: {row[0]}, Title: {row[1]}, UserID: {row[2]}')
    
    if 'quiz_submissions' in tables:
        print('\n=== Sample Submission ===')
        result5 = conn.execute(text('SELECT id, quiz_id, user_id, score, percentage FROM quiz_submissions LIMIT 1'))
        for row in result5:
            print(f'  ID: {row[0]}, QuizID: {row[1]}, UserID: {row[2]}, Score: {row[3]}, %: {row[4]}')
