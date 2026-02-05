from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    # Check existing tables
    result = conn.execute(text("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public'
    """))
    print('=== Existing Tables ===')
    for row in result:
        print(f'  - {row[0]}')
    
    # Check quizzes table columns
    result = conn.execute(text("""
        SELECT column_name, data_type FROM information_schema.columns 
        WHERE table_name = 'quizzes' ORDER BY ordinal_position
    """))
    print('\n=== Quizzes Table Columns ===')
    for row in result:
        print(f'  - {row[0]}: {row[1]}')
    
    # Check users table
    result = conn.execute(text("""
        SELECT column_name, data_type FROM information_schema.columns 
        WHERE table_name = 'users' ORDER BY ordinal_position
    """))
    print('\n=== Users Table Columns ===')
    for row in result:
        print(f'  - {row[0]}: {row[1]}')
    
    # Count rows
    result = conn.execute(text('SELECT COUNT(*) FROM quizzes'))
    print(f'\n=== Row Counts ===')
    print(f'  Quizzes: {result.scalar()}')
    
    result = conn.execute(text('SELECT COUNT(*) FROM users'))
    print(f'  Users: {result.scalar()}')

print('\nDatabase check complete!')
