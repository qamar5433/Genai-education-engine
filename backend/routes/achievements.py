from flask import Blueprint, jsonify, session
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import SessionLocal
from models import User, QuizAttempt

achievements_bp = Blueprint("achievements", __name__)

ALL_BADGES = [
    {"id":"first_quiz",    "name":"First Steps",       "desc":"Complete your first quiz",               "icon":"quiz",              "color":"#4746E5","xp":50},
    {"id":"quiz_5",        "name":"Quiz Enthusiast",   "desc":"Complete 5 quizzes",                     "icon":"military_tech",     "color":"#06B6D4","xp":100},
    {"id":"quiz_25",       "name":"Quiz Master",        "desc":"Complete 25 quizzes",                    "icon":"workspace_premium", "color":"#F59E0B","xp":250},
    {"id":"streak_3",      "name":"On Fire",            "desc":"Maintain a 3-day streak",                "icon":"local_fire_department","color":"#EF4444","xp":75},
    {"id":"streak_7",      "name":"Week Warrior",       "desc":"Maintain a 7-day streak",                "icon":"whatshot",          "color":"#F97316","xp":150},
    {"id":"streak_30",     "name":"Monthly Legend",     "desc":"Maintain a 30-day streak",               "icon":"star",              "color":"#FBBF24","xp":500},
    {"id":"xp_100",        "name":"XP Hunter",          "desc":"Earn 100 XP",                            "icon":"bolt",              "color":"#8B5CF6","xp":50},
    {"id":"xp_500",        "name":"XP Champion",        "desc":"Earn 500 XP",                            "icon":"emoji_events",      "color":"#EC4899","xp":100},
    {"id":"xp_1000",       "name":"Elite Learner",      "desc":"Earn 1000 XP",                           "icon":"diamond",           "color":"#06B6D4","xp":200},
    {"id":"perfect_score", "name":"Perfectionist",      "desc":"Score 100% on a quiz",                   "icon":"grade",             "color":"#22C55E","xp":200},
    {"id":"content_first", "name":"Content Creator",    "desc":"Generate your first content",            "icon":"auto_fix_high",     "color":"#4746E5","xp":50},
    {"id":"top_3",         "name":"Podium Finisher",    "desc":"Reach top 3 on the leaderboard",         "icon":"social_leaderboard","color":"#F59E0B","xp":300},
]

def check_achievements(user_id, db):
    user     = db.query(User).filter_by(id=user_id).first()
    if not user: return []
    attempts = db.query(QuizAttempt).filter_by(user_id=user_id).all()
    unlocked = []

    if len(attempts) >= 1:  unlocked.append("first_quiz")
    if len(attempts) >= 5:  unlocked.append("quiz_5")
    if len(attempts) >= 25: unlocked.append("quiz_25")
    if user.streak >= 3:    unlocked.append("streak_3")
    if user.streak >= 7:    unlocked.append("streak_7")
    if user.streak >= 30:   unlocked.append("streak_30")
    if user.xp >= 100:      unlocked.append("xp_100")
    if user.xp >= 500:      unlocked.append("xp_500")
    if user.xp >= 1000:     unlocked.append("xp_1000")
    if any(a.score >= 100 for a in attempts): unlocked.append("perfect_score")

    return unlocked

@achievements_bp.route("/api/achievements", methods=["GET"])
def get_achievements():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    db = SessionLocal()
    try:
        unlocked = check_achievements(session["user_id"], db)
        result   = [{**b, "unlocked": b["id"] in unlocked} for b in ALL_BADGES]
        total    = len(ALL_BADGES)
        earned   = len(unlocked)
        return jsonify({
            "badges": result,
            "total":  total,
            "earned": earned,
            "pct":    round((earned / total) * 100)
        })
    finally:
        db.close()
