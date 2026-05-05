from flask import Blueprint, jsonify, request, session, Response, stream_with_context
import json
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import SessionLocal
from models import Quiz, Question, QuizAttempt, User, Course, Enrollment
from datetime import datetime

quiz_bp = Blueprint("quiz", __name__)

@quiz_bp.route("/api/quizzes", methods=["GET"])
def get_quizzes():
    uid = session.get("user_id")
    if not uid:
        return jsonify({"error": "Not authenticated"}), 401
    db = SessionLocal()
    try:
        # Get all quizzes (both pre-seeded and AI-generated)
        quizzes = db.query(Quiz).all()
        result = []
        for q in quizzes:
            course = db.query(Course).filter_by(id=q.course_id).first() if q.course_id else None
            attempts = db.query(QuizAttempt).filter_by(user_id=uid, quiz_id=q.id).count()
            best = db.query(QuizAttempt).filter_by(user_id=uid, quiz_id=q.id).order_by(QuizAttempt.score.desc()).first()
            result.append({
                "id": q.id, "title": q.title, "difficulty": q.difficulty,
                "time_limit_min": q.time_limit_min, "description": q.description,
                "course": course.title if course else "Custom AI Quiz", 
                "topic": course.topic if course else "AI Generated",
                "question_count": db.query(Question).filter_by(quiz_id=q.id).count(),
                "attempts": attempts, "best_score": round(best.score, 1) if best else None
            })
        return jsonify({"quizzes": result}), 200
    finally:
        db.close()

@quiz_bp.route("/api/quizzes/<int:quiz_id>", methods=["GET"])
def get_quiz(quiz_id):
    uid = session.get("user_id")
    if not uid:
        return jsonify({"error": "Not authenticated"}), 401
    db = SessionLocal()
    try:
        quiz = db.query(Quiz).filter_by(id=quiz_id).first()
        if not quiz:
            return jsonify({"error": "Quiz not found"}), 404
        questions = db.query(Question).filter_by(quiz_id=quiz_id).all()
        q_list = [{"id": q.id, "text": q.text, "option_a": q.option_a, "option_b": q.option_b, "option_c": q.option_c, "option_d": q.option_d} for q in questions]
        course = db.query(Course).filter_by(id=quiz.course_id).first() if quiz.course_id else None
        return jsonify({
            "id": quiz.id, "title": quiz.title, "difficulty": quiz.difficulty,
            "time_limit_min": quiz.time_limit_min, "description": quiz.description,
            "course": course.title if course else "Custom AI Quiz",
            "questions": q_list
        }), 200
    finally:
        db.close()

@quiz_bp.route("/api/quiz/generate", methods=["POST"])
def generate_quiz():
    uid = session.get("user_id")
    if not uid:
        return jsonify({"error": "Not authenticated"}), 401
    
    data = request.get_json()
    topic      = data.get("topic", "").strip()
    difficulty = data.get("difficulty", "Medium")
    count      = data.get("count", 5)
    course_id  = data.get("course_id") # New: tie to course
    
    if not topic:
        return jsonify({"error": "Topic is required"}), 400
        
    db = SessionLocal()
    try:
        from ai_client import generate_quiz_ai
        questions_data = generate_quiz_ai(topic, difficulty, count)
        
        # Create a new custom quiz
        new_quiz = Quiz(
            course_id=course_id, # Now using passed course_id
            title=f"AI Quiz: {topic}",
            difficulty=difficulty,
            time_limit_min=count * 2, # 2 mins per question
            description=f"Auto-generated {difficulty} quiz on {topic}."
        )
        db.add(new_quiz)
        db.flush() # Get the new quiz ID
        
        # Add questions
        for q_dict in questions_data:
            q = Question(
                quiz_id=new_quiz.id,
                text=q_dict.get("text", "Error loading question"),
                option_a=q_dict.get("option_a", "A"),
                option_b=q_dict.get("option_b", "B"),
                option_c=q_dict.get("option_c", "C"),
                option_d=q_dict.get("option_d", "D"),
                correct_option=q_dict.get("correct_option", "a"),
                explanation=q_dict.get("explanation", "AI generated question.")
            )
            db.add(q)
            
        db.commit()
        return jsonify({"success": True, "quiz_id": new_quiz.id}), 201
        
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@quiz_bp.route("/api/quiz/generate_stream", methods=["POST"])
def generate_stream():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    data       = request.get_json() or {}
    topic      = data.get("topic", "").strip()
    difficulty = data.get("difficulty", "Medium")
    count      = int(data.get("count", 5))

    if not topic:
        return jsonify({"error": "Topic is required"}), 400

    def generate():
        try:
            from ai_client import generate_quiz_ai_stream
            for token in generate_quiz_ai_stream(topic, difficulty, count):
                yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        yield "data: [DONE]\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@quiz_bp.route("/api/quiz/save_generated", methods=["POST"])
def save_generated():
    uid = session.get("user_id")
    if not uid:
        return jsonify({"error": "Not authenticated"}), 401
    
    data = request.get_json()
    topic = data.get("topic", "Custom Topic")
    difficulty = data.get("difficulty", "Medium")
    course_id = data.get("course_id") # New
    quiz_input = data.get("quiz", [])
    
    # Normalize input: if it's a list, wrap it. If it's a dict with 'questions', use that.
    questions_list = []
    title = f"AI Quiz: {topic}"
    
    if isinstance(quiz_input, list):
        questions_list = quiz_input
    elif isinstance(quiz_input, dict):
        questions_list = quiz_input.get("questions", [])
        title = quiz_input.get("quiz_title", title)

    if not questions_list:
        return jsonify({"error": "No questions found in quiz data"}), 400

    db = SessionLocal()
    try:
        new_quiz = Quiz(
            course_id=course_id,
            title=title,
            difficulty=difficulty,
            time_limit_min=len(questions_list) * 2 or 10,
            description=f"Auto-generated {difficulty} quiz on {topic}."
        )
        db.add(new_quiz)
        db.flush()

        for q_dict in questions_list:
            # Map various possible field names
            q_text = q_dict.get("text") or q_dict.get("q") or q_dict.get("question")
            opt_a = q_dict.get("option_a") or q_dict.get("options", ["A"])[0] if q_dict.get("option_a") or q_dict.get("options") else "A"
            opt_b = q_dict.get("option_b") or q_dict.get("options", ["A","B"])[1] if q_dict.get("option_b") or (q_dict.get("options") and len(q_dict.get("options"))>1) else "B"
            opt_c = q_dict.get("option_c") or q_dict.get("options", ["A","B","C"])[2] if q_dict.get("option_c") or (q_dict.get("options") and len(q_dict.get("options"))>2) else "C"
            opt_d = q_dict.get("option_d") or q_dict.get("options", ["A","B","C","D"])[3] if q_dict.get("option_d") or (q_dict.get("options") and len(q_dict.get("options"))>3) else "D"
            
            # Map correct option
            correct = q_dict.get("correct_option") or q_dict.get("answer")
            if isinstance(correct, int): # if it's 0,1,2,3
                correct = chr(97 + correct)
            elif not correct:
                correct = "a"
            
            q = Question(
                quiz_id=new_quiz.id,
                text=q_text,
                option_a=opt_a,
                option_b=opt_b,
                option_c=opt_c,
                option_d=opt_d,
                correct_option=str(correct).lower(),
                explanation=q_dict.get("explanation", "AI generated question.")
            )
            db.add(q)
        
        db.commit()
        return jsonify({"success": True, "quiz_id": new_quiz.id}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@quiz_bp.route("/api/quiz/submit", methods=["POST"])
def submit_quiz():
    uid = session.get("user_id")
    if not uid:
        return jsonify({"error": "Not authenticated"}), 401
    data = request.get_json()
    quiz_id = data.get("quiz_id")
    answers = data.get("answers", {})  # {question_id: selected_option}
    time_taken = data.get("time_taken_sec", 0)
    db = SessionLocal()
    try:
        questions = db.query(Question).filter_by(quiz_id=quiz_id).all()
        correct = 0
        result_details = []
        for q in questions:
            selected = answers.get(str(q.id), "")
            is_correct = selected.lower() == q.correct_option.lower()
            if is_correct:
                correct += 1
            result_details.append({"question_id": q.id, "text": q.text, "selected": selected, "correct": q.correct_option, "is_correct": is_correct, "explanation": q.explanation})
        total = len(questions)
        score = (correct / total * 100) if total > 0 else 0
        attempt = QuizAttempt(user_id=uid, quiz_id=quiz_id, score=score, total_questions=total, correct_answers=correct, time_taken_sec=time_taken, completed_at=datetime.utcnow())
        db.add(attempt)
        
        # Award XP
        xp_earned = int(score * 0.5) + (20 if time_taken < 120 else 0)
        user = db.query(User).filter_by(id=uid).first()
        user.xp += xp_earned
        
        # NEW: Update Course Progress if applicable
        quiz = db.query(Quiz).filter_by(id=quiz_id).first()
        if quiz and quiz.course_id:
            enrollment = db.query(Enrollment).filter_by(user_id=uid, course_id=quiz.course_id).first()
            if enrollment:
                # Advance progress by 10% (capped at 100) or calculate based on units
                increment = 10.0 if score > 50 else 5.0 # Give more progress for passing scores
                enrollment.progress_pct = min(100.0, (enrollment.progress_pct or 0) + increment)
                enrollment.last_active = datetime.utcnow()
                if enrollment.progress_pct >= (enrollment.completed_units + 1) * 10:
                    enrollment.completed_units = min(enrollment.completed_units + 1, quiz.course.total_units if quiz.course else 10)

        db.commit()
        return jsonify({"score": round(score, 1), "correct": correct, "total": total, "xp_earned": xp_earned, "details": result_details}), 200
    finally:
        db.close()

@quiz_bp.route("/api/courses/enrolled", methods=["GET"])
def enrolled_courses():
    uid = session.get("user_id")
    if not uid:
        return jsonify({"error": "Not authenticated"}), 401
    db = SessionLocal()
    try:
        enrollments = db.query(Enrollment).filter_by(user_id=uid).all()
        result = []
        for enr in enrollments:
            c = db.query(Course).filter_by(id=enr.course_id).first()
            if c:
                quizzes = db.query(Quiz).filter_by(course_id=c.id).all()
                result.append({
                    "id": c.id, "title": c.title, "topic": c.topic, "description": c.description,
                    "icon": c.icon, "color": c.color, "total_units": c.total_units,
                    "completed_units": enr.completed_units, "progress_pct": enr.progress_pct,
                    "quiz_count": len(quizzes),
                    "last_active": enr.last_active.strftime("%Y-%m-%d")
                })
        all_courses = db.query(Course).all()
        enrolled_ids = [enr.course_id for enr in enrollments]
        available = []
        for c in all_courses:
            if c.id not in enrolled_ids:
                available.append({"id": c.id, "title": c.title, "topic": c.topic, "description": c.description, "icon": c.icon, "color": c.color, "total_units": c.total_units})
        return jsonify({"enrolled": result, "available": available}), 200
    finally:
        db.close()

@quiz_bp.route("/api/courses/<int:course_id>/enroll", methods=["POST"])
def enroll_course(course_id):
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
            return jsonify({"error": "Already enrolled"}), 400
            
        # Create new enrollment
        enrollment = Enrollment(
            user_id=uid,
            course_id=course_id,
            progress_pct=0.0,
            completed_units=0,
            last_active=datetime.utcnow()
        )
        db.add(enrollment)
        db.commit()
        
        return jsonify({"success": True, "message": f"Successfully enrolled in {course.title}"}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()
