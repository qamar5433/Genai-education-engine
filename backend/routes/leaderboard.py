from flask import Blueprint, jsonify, session
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import SessionLocal
from models import LeaderboardEntry, User, Achievement, UserAchievement

leaderboard_bp = Blueprint("leaderboard", __name__)

@leaderboard_bp.route("/api/leaderboard", methods=["GET"])
def get_leaderboard():
    uid = session.get("user_id")
    if not uid:
        return jsonify({"error": "Not authenticated"}), 401
    db = SessionLocal()
    try:
        entries = db.query(LeaderboardEntry).order_by(LeaderboardEntry.weekly_xp.desc()).all()
        board = []
        my_rank = None
        for i, entry in enumerate(entries):
            u = db.query(User).filter_by(id=entry.user_id).first()
            if u:
                board.append({
                    "rank": i + 1, "name": u.name, "level": u.level,
                    "weekly_xp": entry.weekly_xp, "streak": u.streak,
                    "is_current_user": entry.user_id == uid
                })
                if entry.user_id == uid:
                    my_rank = i + 1

        # All achievements
        all_achievements = db.query(Achievement).all()
        ach_list = []
        for ach in all_achievements:
            ua = db.query(UserAchievement).filter_by(user_id=uid, achievement_id=ach.id).first()
            ach_list.append({
                "id": ach.id, "title": ach.title, "description": ach.description,
                "icon": ach.icon, "xp_reward": ach.xp_reward,
                "unlocked": ua is not None,
                "unlocked_at": ua.unlocked_at.strftime("%Y-%m-%d") if ua else None
            })

        return jsonify({"leaderboard": board, "my_rank": my_rank, "achievements": ach_list}), 200
    finally:
        db.close()
