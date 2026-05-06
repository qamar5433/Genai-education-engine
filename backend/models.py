"""
backend/models.py
─────────────────
SQLAlchemy ORM models for GENAI EDUCATION ENGINE.

User OTP / Auth fields added:
  is_verified          – True once email is confirmed via OTP
  otp_code             – 6-digit verification OTP (plaintext, short-lived)
  otp_expires_at       – UTC expiry for verification OTP (5 minutes)
  otp_resend_at        – last time any OTP was sent (enforces 60-sec cooldown)
  reset_otp            – 6-digit password-reset OTP (plaintext, short-lived)
  reset_otp_expires_at – UTC expiry for password-reset OTP (5 minutes)
"""

from sqlalchemy import Column, Integer, String, Float, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime


# ─────────────────────────── User ───────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    name          = Column(String(100), nullable=False)
    email         = Column(String(200), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    xp            = Column(Integer,  default=0)
    streak        = Column(Integer,  default=0)
    level         = Column(String(50),  default="Beginner I")
    avatar_url    = Column(String(500), default="")
    created_at    = Column(DateTime, default=datetime.utcnow)

    # ── Email verification ────────────────────────────────────────────────
    is_verified    = Column(Boolean,    default=True)
    otp_code       = Column(String(10), nullable=True)
    otp_expires_at = Column(DateTime,   nullable=True)

    # Rate-limit: UTC timestamp of last OTP send (any kind)
    otp_resend_at  = Column(DateTime,   nullable=True)

    # ── Password reset ────────────────────────────────────────────────────
    reset_otp            = Column(String(10), nullable=True)
    reset_otp_expires_at = Column(DateTime,   nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────
    enrollments       = relationship("Enrollment",       back_populates="user")
    quiz_attempts     = relationship("QuizAttempt",      back_populates="user")
    tutor_sessions    = relationship("TutorSession",     back_populates="user")
    user_achievements = relationship("UserAchievement",  back_populates="user")
    leaderboard_entry = relationship("LeaderboardEntry", back_populates="user", uselist=False)


# ─────────────────────────── Course ─────────────────────────────────────────

class Course(Base):
    __tablename__ = "courses"

    id          = Column(Integer, primary_key=True, index=True)
    title       = Column(String(200), nullable=False)
    description = Column(Text)
    topic       = Column(String(100))
    total_units = Column(Integer, default=10)
    icon        = Column(String(50), default="school")
    color       = Column(String(50), default="blue")

    enrollments = relationship("Enrollment", back_populates="course")
    quizzes     = relationship("Quiz",       back_populates="course")


# ─────────────────────────── Enrollment ─────────────────────────────────────

class Enrollment(Base):
    __tablename__ = "enrollments"

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id"))
    course_id       = Column(Integer, ForeignKey("courses.id"))
    progress_pct    = Column(Float,   default=0.0)
    last_active     = Column(DateTime, default=datetime.utcnow)
    completed_units = Column(Integer,  default=0)

    user   = relationship("User",   back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")


# ─────────────────────────── Quiz ───────────────────────────────────────────

class Quiz(Base):
    __tablename__ = "quizzes"

    id             = Column(Integer, primary_key=True, index=True)
    course_id      = Column(Integer, ForeignKey("courses.id"))
    title          = Column(String(200), nullable=False)
    difficulty     = Column(String(50),  default="Medium")
    time_limit_min = Column(Integer,     default=10)
    description    = Column(Text)

    course    = relationship("Course",      back_populates="quizzes")
    questions = relationship("Question",    back_populates="quiz")
    attempts  = relationship("QuizAttempt", back_populates="quiz")


# ─────────────────────────── Question ───────────────────────────────────────

class Question(Base):
    __tablename__ = "questions"

    id             = Column(Integer, primary_key=True, index=True)
    quiz_id        = Column(Integer, ForeignKey("quizzes.id"))
    text           = Column(Text, nullable=False)
    option_a       = Column(Text)
    option_b       = Column(Text)
    option_c       = Column(Text)
    option_d       = Column(Text)
    correct_option = Column(String(1))   # "a", "b", "c", or "d"
    explanation    = Column(Text)

    quiz = relationship("Quiz", back_populates="questions")


# ─────────────────────────── QuizAttempt ────────────────────────────────────

class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id"))
    quiz_id         = Column(Integer, ForeignKey("quizzes.id"))
    score           = Column(Float,   default=0.0)
    total_questions = Column(Integer)
    correct_answers = Column(Integer)
    time_taken_sec  = Column(Integer,  default=0)
    completed_at    = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="quiz_attempts")
    quiz = relationship("Quiz", back_populates="attempts")


# ─────────────────────────── TutorSession ───────────────────────────────────

class TutorSession(Base):
    __tablename__ = "tutor_sessions"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"))
    started_at = Column(DateTime, default=datetime.utcnow)

    user     = relationship("User",         back_populates="tutor_sessions")
    messages = relationship("TutorMessage", back_populates="session")


# ─────────────────────────── TutorMessage ───────────────────────────────────

class TutorMessage(Base):
    __tablename__ = "tutor_messages"

    id         = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("tutor_sessions.id"))
    role       = Column(String(10))   # "user" or "ai"
    content    = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("TutorSession", back_populates="messages")


# ─────────────────────────── Achievement ────────────────────────────────────

class Achievement(Base):
    __tablename__ = "achievements"

    id          = Column(Integer, primary_key=True, index=True)
    title       = Column(String(100))
    description = Column(Text)
    icon        = Column(String(50))
    xp_reward   = Column(Integer, default=100)

    user_achievements = relationship("UserAchievement", back_populates="achievement")


class UserAchievement(Base):
    __tablename__ = "user_achievements"

    id             = Column(Integer, primary_key=True, index=True)
    user_id        = Column(Integer, ForeignKey("users.id"))
    achievement_id = Column(Integer, ForeignKey("achievements.id"))
    unlocked_at    = Column(DateTime, default=datetime.utcnow)

    user        = relationship("User",        back_populates="user_achievements")
    achievement = relationship("Achievement", back_populates="user_achievements")


# ─────────────────────────── LeaderboardEntry ───────────────────────────────

class LeaderboardEntry(Base):
    __tablename__ = "leaderboard_entries"

    id        = Column(Integer, primary_key=True, index=True)
    user_id   = Column(Integer, ForeignKey("users.id"), unique=True)
    weekly_xp = Column(Integer, default=0)
    rank      = Column(Integer, default=0)

    user = relationship("User", back_populates="leaderboard_entry")
