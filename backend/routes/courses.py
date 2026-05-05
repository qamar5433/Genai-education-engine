from flask import Blueprint, jsonify, session, request
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import SessionLocal
from models import User, Course, Enrollment
from datetime import datetime

courses_bp = Blueprint("courses", __name__)

@courses_bp.route("/api/courses/enrolled", methods=["GET"])
def get_courses_status():
    uid = session.get("user_id")
    if not uid:
        return jsonify({"error": "Not authenticated"}), 401
    
    db = SessionLocal()
    try:
        # Get all enrollments for this user
        user_enrollments = db.query(Enrollment).filter_by(user_id=uid).all()
        enrolled_ids = [e.course_id for e in user_enrollments]
        
        # Build list of enrolled courses with progress info
        enrolled_list = []
        for enr in user_enrollments:
            c = db.query(Course).filter_by(id=enr.course_id).first()
            if c:
                enrolled_list.append({
                    "id": c.id,
                    "title": c.title,
                    "description": c.description,
                    "topic": c.topic,
                    "progress_pct": round(enr.progress_pct, 1),
                    "completed_units": enr.completed_units,
                    "total_units": c.total_units,
                    "icon": c.icon,
                    "color": c.color
                })
        
        # Get available courses (not yet enrolled)
        available_courses = db.query(Course).filter(~Course.id.in_(enrolled_ids)).all()
        available_list = [{
            "id": c.id,
            "title": c.title,
            "topic": c.topic,
            "total_units": c.total_units,
            "icon": c.icon,
            "color": c.color,
            "description": c.description
        } for c in available_courses]
        
        return jsonify({
            "enrolled": enrolled_list,
            "available": available_list
        }), 200
    finally:
        db.close()

@courses_bp.route("/api/courses/<int:course_id>/enroll", methods=["POST"])
def enroll_in_course(course_id):
    uid = session.get("user_id")
    if not uid:
        return jsonify({"error": "Not authenticated"}), 401
    
    db = SessionLocal()
    try:
        # Check if course exists
        course = db.query(Course).filter_by(id=course_id).first()
        if not course:
            return jsonify({"error": "Course not found"}), 404
            
        # Check if already enrolled
        existing = db.query(Enrollment).filter_by(user_id=uid, course_id=course_id).first()
        if existing:
            return jsonify({"message": "Already enrolled in this course"}), 200
            
        # Create enrollment
        new_enr = Enrollment(
            user_id=uid,
            course_id=course_id,
            progress_pct=0.0,
            completed_units=0,
            last_active=datetime.utcnow()
        )
        db.add(new_enr)
        
        # Optional: Award a bit of XP for starting a new course
        user = db.query(User).filter_by(id=uid).first()
        if user:
            user.xp += 20
            
        db.commit()
        return jsonify({"success": True, "message": f"Successfully enrolled in {course.title}!"}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()
@courses_bp.route("/api/courses/complete_unit", methods=["POST"])
def complete_unit():
    uid = session.get("user_id")
    if not uid:
        return jsonify({"error": "Not authenticated"}), 401
    
    data = request.get_json()
    course_id = data.get("course_id")
    if not course_id:
        return jsonify({"error": "Course ID required"}), 400
        
    db = SessionLocal()
    try:
        enr = db.query(Enrollment).filter_by(user_id=uid, course_id=course_id).first()
        if not enr:
            return jsonify({"error": "Enrollment not found"}), 404
            
        course = db.query(Course).filter_by(id=course_id).first()
        if not course:
             return jsonify({"error": "Course not found"}), 404

        # Increment units if not already at max
        if enr.completed_units < course.total_units:
            enr.completed_units += 1
            # Update progress based on units
            enr.progress_pct = (enr.completed_units / course.total_units) * 100
        
        enr.last_active = datetime.utcnow()
        
        # Award XP for completing a unit
        user = db.query(User).filter_by(id=uid).first()
        if user:
            user.xp += 50
            
        db.commit()
        return jsonify({
            "success": True, 
            "completed_units": enr.completed_units, 
            "progress_pct": round(enr.progress_pct, 1),
            "xp_earned": 50
        }), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()
