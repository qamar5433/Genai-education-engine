from flask import Blueprint, jsonify, session
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import SessionLocal
from models import User, Enrollment, QuizAttempt, Course, UserAchievement, Achievement
from datetime import datetime, timedelta

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/api/dashboard", methods=["GET"])
def get_dashboard():
    uid = session.get("user_id")
    if not uid:
        return jsonify({"error": "Not authenticated"}), 401
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(id=uid).first()
        if not user:
            return jsonify({"error": "Not found"}), 404

        # Enrollments with course info
        enrollments = db.query(Enrollment).filter_by(user_id=uid).all()
        active_course = None
        if enrollments:
            latest = max(enrollments, key=lambda e: e.last_active)
            c = db.query(Course).filter_by(id=latest.course_id).first()
            active_course = {
                "id": c.id, "title": c.title, "topic": c.topic, "progress": latest.progress_pct,
                "completed_units": latest.completed_units, "total_units": c.total_units,
                "icon": c.icon, "color": c.color,
                "last_active": latest.last_active.strftime("%Y-%m-%d %H:%M")
            }

        # Recent quiz scores (last 7)
        attempts = db.query(QuizAttempt).filter_by(user_id=uid).order_by(QuizAttempt.completed_at.desc()).limit(7).all()
        scores = [{"score": round(a.score, 1), "date": a.completed_at.strftime("%a")} for a in reversed(attempts)]
        avg_score = round(sum(a.score for a in attempts) / len(attempts), 1) if attempts else 0

        # Achievements
        uas = db.query(UserAchievement).filter_by(user_id=uid).all()
        achievements = []
        for ua in uas:
            ach = db.query(Achievement).filter_by(id=ua.achievement_id).first()
            if ach:
                achievements.append({"title": ach.title, "icon": ach.icon, "xp_reward": ach.xp_reward})

        # Enrolled courses for ecosystem cards
        courses_enrolled = []
        for enr in enrollments:
            c = db.query(Course).filter_by(id=enr.course_id).first()
            if c:
                courses_enrolled.append({"id": c.id, "title": c.title, "topic": c.topic, "progress": enr.progress_pct, "icon": c.icon, "color": c.color})

        return jsonify({
            "user": {"name": user.name, "xp": user.xp, "streak": user.streak, "level": user.level},
            "active_course": active_course,
            "quiz_scores": scores,
            "avg_score": avg_score,
            "achievements": achievements,
            "enrolled_courses": courses_enrolled,
            "weekly_goal_pct": min(100, round((user.streak / 7) * 100)),
        }), 200
    finally:
        db.close()
