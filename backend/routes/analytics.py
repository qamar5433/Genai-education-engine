from flask import Blueprint, jsonify, session
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import SessionLocal
from models import QuizAttempt, Quiz, Course, Enrollment
from datetime import datetime, timedelta

analytics_bp = Blueprint("analytics", __name__)

@analytics_bp.route("/api/analytics", methods=["GET"])
def get_analytics():
    uid = session.get("user_id")
    if not uid:
        return jsonify({"error": "Not authenticated"}), 401
    
    response = None
    db = SessionLocal()
    try:
        # All attempts
        attempts = db.query(QuizAttempt).filter_by(user_id=uid).order_by(QuizAttempt.completed_at).all()
        
        # Pre-fetch all quizzes AND their associated courses
        quiz_ids = list(set(a.quiz_id for a in attempts if a.quiz_id))
        quizzes = db.query(Quiz).filter(Quiz.id.in_(quiz_ids)).all() if quiz_ids else []
        quizzes_map = {q.id: q for q in quizzes}

        # Weekly scores (last 7 days, one per day)
        weekly = []
        now = datetime.utcnow()
        for i in range(6, -1, -1):
            day = now - timedelta(days=i)
            day_attempts = [a for a in attempts if a.completed_at and a.completed_at.date() == day.date()]
            avg = round(sum((a.score or 0) for a in day_attempts) / len(day_attempts), 1) if day_attempts else 0
            weekly.append({"day": day.strftime("%a"), "score": avg})

        # Per-course progress
        enrollments = db.query(Enrollment).filter_by(user_id=uid).all()
        course_progress = []
        for enr in enrollments:
            c = db.query(Course).filter_by(id=enr.course_id).first()
            if c:
                # Optimized: Filter attempts that belong to this course
                course_attempts = [a for a in attempts if quizzes_map.get(a.quiz_id) and quizzes_map[a.quiz_id].course_id == c.id]
                avg_score = round(sum((a.score or 0) for a in course_attempts) / len(course_attempts), 1) if course_attempts else 0
                course_progress.append({
                    "course": c.title, "topic": c.topic, "progress": enr.progress_pct or 0,
                    "avg_score": avg_score, "quizzes_taken": len(course_attempts),
                    "icon": c.icon, "color": c.color
                })

        # Summary stats
        total_quizzes = len(attempts)
        avg_score_all = round(sum((a.score or 0) for a in attempts) / total_quizzes, 1) if attempts else 0
        best_score = round(max(((a.score or 0) for a in attempts), default=0), 1)
        avg_time = round(sum((a.time_taken_sec or 0) for a in attempts) / total_quizzes, 0) if attempts else 0

        # Monthly trend (last 4 weeks)
        monthly = []
        for w in range(3, -1, -1):
            start = now - timedelta(weeks=w+1)
            end = now - timedelta(weeks=w)
            week_atts = [a for a in attempts if a.completed_at and start <= a.completed_at <= end]
            avg = round(sum((a.score or 0) for a in week_atts) / len(week_atts), 1) if week_atts else 0
            monthly.append({"week": f"Week {4-w}", "score": avg, "quizzes": len(week_atts)})

        # Skill radar data (simulated topic mastery)
        skill_labels = ["Problem Solving", "Memory Recall", "Critical Thinking", "Speed", "Accuracy", "Consistency"]
        if attempts:
            base_skill = avg_score_all
            skill_values = [min(100, max(0, base_skill + ((i % 3) - 1) * 3)) for i in range(len(skill_labels))]
        else:
            skill_values = [0 for _ in skill_labels]

        # Recent Activity (Last 10 attempts)
        recent_activity = []
        for a in sorted(attempts, key=lambda x: x.completed_at, reverse=True)[:10]:
            q = quizzes_map.get(a.quiz_id)
            title = q.title if q and q.title else "Quiz"
            # Get topic from Course if it exists, else use title or General
            topic = "General"
            if q:
                if q.course and q.course.topic:
                    topic = q.course.topic
                elif "AI Quiz: " in title:
                    topic = title.replace("AI Quiz: ", "")
            
            recent_activity.append({
                "quiz_title": title,
                "score": a.score or 0,
                "date": a.completed_at.strftime("%b %d, %H:%M") if a.completed_at else "Recent",
                "topic": topic,
                "time_sec": a.time_taken_sec or 0
            })

        # Topic Mastery Breakdown
        topic_scores = {}
        for a in attempts:
            q = quizzes_map.get(a.quiz_id)
            if not q: continue
            title = q.title if q.title else "Quiz"
            
            # Use same topic extraction logic
            t = "General"
            if q.course and q.course.topic:
                t = q.course.topic
            elif "AI Quiz: " in title:
                t = title.replace("AI Quiz: ", "")
                
            if t not in topic_scores: topic_scores[t] = []
            topic_scores[t].append(a.score or 0)
        
        mastery_breakdown = []
        for t, scores in topic_scores.items():
            avg = round(sum(scores)/len(scores), 1)
            mastery_breakdown.append({"topic": t, "avg_score": avg, "count": len(scores)})
        mastery_breakdown.sort(key=lambda x: x["avg_score"], reverse=True)

        from models import User
        user = db.query(User).filter_by(id=uid).first()
        user_streak = user.streak if user else 0

        # Smart Insights (identifying weakest areas)
        weak_topics = [m["topic"] for m in mastery_breakdown if m["avg_score"] < 60]
        insights = []
        if weak_topics:
            insights.append(f"Focus on {weak_topics[0]} - your average score is below 60%.")
        if total_quizzes > 0 and avg_score_all > 80:
            insights.append("Great consistency! Try taking 'Hard' difficulty quizzes to push your limits.")
        elif total_quizzes < 5:
            insights.append("Complete more quizzes to unlock personalized AI exam predictions.")

        response = jsonify({
            "summary": {"total_quizzes": total_quizzes, "avg_score": avg_score_all, "best_score": best_score, "avg_time_sec": int(avg_time), "streak": user_streak},
            "weekly_scores": weekly,
            "course_progress": course_progress,
            "skill_radar": {"labels": skill_labels, "values": skill_values},
            "monthly_trend": monthly,
            "recent_activity": recent_activity,
            "topic_mastery": mastery_breakdown,
            "insights": insights,
            "prediction": {"exam_score": min(100, round(avg_score_all + min(5, len(attempts) * 0.5), 1)) if attempts else 0, "confidence": min(99, max(50, 50 + len(attempts) * 2)) if attempts else 0}
        })
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response, 200
    except Exception as e:
        import traceback
        err_msg = f"Analytics Error: {str(e)}\n{traceback.format_exc()}"
        print(err_msg)
        with open("analytics_error.log", "a") as f:
            f.write(f"\n--- {datetime.utcnow()} ---\n{err_msg}\n")
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()
