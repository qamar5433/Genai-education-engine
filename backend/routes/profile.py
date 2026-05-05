from flask import Blueprint, request, jsonify, session
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import SessionLocal
from models import User, QuizAttempt, TutorSession
from sqlalchemy import func
from datetime import datetime

profile_bp = Blueprint("profile", __name__)

@profile_bp.route("/api/profile", methods=["GET"])
def get_profile():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(id=session["user_id"]).first()
        if not user:
            return jsonify({"error": "User not found"}), 404

        total_quizzes  = db.query(QuizAttempt).filter_by(user_id=user.id).count()
        avg_score_val  = db.query(func.avg(QuizAttempt.score)).filter_by(user_id=user.id).scalar()
        avg_score      = round(float(avg_score_val or 0), 1)
        tutor_sessions = db.query(TutorSession).filter_by(user_id=user.id).count()
        joined         = user.created_at.strftime("%B %Y") if user.created_at else "2024"

        return jsonify({
            "id":             user.id,
            "name":           user.name,
            "email":          user.email,
            "xp":             user.xp,
            "level":          user.level,
            "streak":         user.streak,
            "avatar_color":   getattr(user, "avatar_color", "#4746E5"),
            "bio":            getattr(user, "bio", ""),
            "joined":         joined,
            "total_quizzes":  total_quizzes,
            "avg_score":      avg_score,
            "tutor_sessions": tutor_sessions,
        })
    finally:
        db.close()

@profile_bp.route("/api/profile", methods=["PUT"])
def update_profile():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(id=session["user_id"]).first()
        if not user:
            return jsonify({"error": "User not found"}), 404

        data = request.get_json() or {}
        if "name" in data and data["name"].strip():
            user.name = data["name"].strip()[:80]
        # bio / avatar_color are extended fields — store if attr exists
        if "bio" in data:
            try: user.bio = data["bio"][:300]
            except: pass
        if "avatar_color" in data:
            try: user.avatar_color = data["avatar_color"]
            except: pass

        db.commit()
        session["user_name"] = user.name
        return jsonify({"success": True, "name": user.name})
    finally:
        db.close()
