from flask import Blueprint, request, jsonify, session
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import SessionLocal
from models import Enrollment, User

progress_bp = Blueprint("progress", __name__)

@progress_bp.route("/api/progress/mark", methods=["POST"])
def mark_progress():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    data = request.get_json() or {}
    course_id  = data.get("course_id")
    if not course_id:
        return jsonify({"error": "course_id required"}), 400

    db = SessionLocal()
    try:
        enrollment = db.query(Enrollment).filter_by(
            user_id=session["user_id"], course_id=course_id
        ).first()
        if not enrollment:
            return jsonify({"error": "Enrollment not found"}), 404

        # Advance progress
        new_progress = min(100.0, (enrollment.progress_pct or 0) + 10.0)
        enrollment.progress_pct = new_progress
        new_units = min(enrollment.completed_units + 1, enrollment.course.total_units if enrollment.course else 10)
        enrollment.completed_units = new_units

        # Award XP
        user = db.query(User).filter_by(id=session["user_id"]).first()
        xp_gain = 50
        user.xp += xp_gain
        db.commit()

        return jsonify({
            "success": True,
            "progress": round(new_progress, 1),
            "completed": new_progress >= 100,
            "xp_gained": xp_gain,
            "total_xp": user.xp
        })
    finally:
        db.close()

@progress_bp.route("/api/progress/<int:course_id>", methods=["GET"])
def get_progress(course_id):
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    db = SessionLocal()
    try:
        enrollment = db.query(Enrollment).filter_by(
            user_id=session["user_id"], course_id=course_id
        ).first()
        if not enrollment:
            return jsonify({"progress": 0, "completed": False})
        return jsonify({
            "progress": round(enrollment.progress_pct or 0, 1),
            "completed": (enrollment.progress_pct or 0) >= 100
        })
    finally:
        db.close()
