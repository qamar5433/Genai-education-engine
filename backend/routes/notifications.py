from flask import Blueprint, jsonify, session
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import SessionLocal
from models import User, QuizAttempt

notifications_bp = Blueprint("notifications", __name__)

@notifications_bp.route("/api/notifications", methods=["GET"])
def get_notifications():
    if "user_id" not in session:
        return jsonify({"notifications": [], "unread": 0})
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(id=session["user_id"]).first()
        if not user:
            return jsonify({"notifications": [], "unread": 0})

        notes = []
        # Streak reminder
        if user.streak > 0:
            notes.append({
                "id": 1, "type": "streak", "icon": "local_fire_department", "color": "#EF4444",
                "title": f"🔥 {user.streak}-day streak!",
                "msg": "Keep it up — study today to maintain it.", "time": "Today"
            })
        # XP milestone
        next_milestone = ((user.xp // 100) + 1) * 100
        notes.append({
            "id": 2, "type": "xp", "icon": "bolt", "color": "#8B5CF6",
            "title": f"⚡ {user.xp} XP earned",
            "msg": f"Just {next_milestone - user.xp} XP to next milestone!", "time": "Today"
        })
        # Quiz suggestion
        attempts = db.query(QuizAttempt).filter_by(user_id=user.id).count()
        if attempts < 5:
            notes.append({
                "id": 3, "type": "quiz", "icon": "quiz", "color": "#4746E5",
                "title": "📝 Take a quiz!",
                "msg": "Quizzes boost retention by 40%. Try one now.", "time": "Suggested"
            })
        # Daily tip
        notes.append({
            "id": 4, "type": "tip", "icon": "auto_awesome", "color": "#06B6D4",
            "title": "💡 Pro Tip",
            "msg": "Generate flashcards right after reading notes for 2× retention.", "time": "Daily tip"
        })

        return jsonify({"notifications": notes, "unread": len(notes)})
    finally:
        db.close()
