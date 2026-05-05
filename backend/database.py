from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "quizgenius.db")

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
SessionLocal = sessionmaker(bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from models import User, Course, Enrollment, Quiz, Question, QuizAttempt, TutorSession, TutorMessage, Achievement, UserAchievement, LeaderboardEntry
    Base.metadata.create_all(bind=engine)
    
    from sqlalchemy import text
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT 1"))
            conn.execute(text("ALTER TABLE users ADD COLUMN otp_code VARCHAR(10)"))
            conn.execute(text("ALTER TABLE users ADD COLUMN otp_expires_at DATETIME"))
    except Exception:
        pass  # Columns already exist
