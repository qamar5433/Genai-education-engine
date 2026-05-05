from flask import Blueprint, request, jsonify, session
import sys, os
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import SessionLocal, Base, engine
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey

library_bp = Blueprint("library", __name__)

# SavedContent model defined here since it's library-specific
class SavedContent(Base):
    __tablename__ = "saved_content"
    __table_args__ = {"extend_existing": True}
    id           = Column(Integer, primary_key=True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False)
    title        = Column(String(200), nullable=False)
    content_type = Column(String(50), nullable=False, default="notes")
    content      = Column(Text, nullable=False)
    word_count   = Column(Integer, default=0)
    created_at   = Column(DateTime, default=datetime.utcnow)

# Ensure table exists
Base.metadata.create_all(bind=engine)

@library_bp.route("/api/library", methods=["GET"])
def get_library():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    db = SessionLocal()
    try:
        items = db.query(SavedContent).filter_by(
            user_id=session["user_id"]
        ).order_by(SavedContent.created_at.desc()).all()
        return jsonify([{
            "id":           i.id,
            "title":        i.title,
            "content_type": i.content_type,
            "content":      i.content,
            "word_count":   i.word_count,
            "created_at":   i.created_at.strftime("%b %d, %Y") if i.created_at else ""
        } for i in items])
    finally:
        db.close()

@library_bp.route("/api/library", methods=["POST"])
def save_to_library():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    data = request.get_json() or {}
    title        = data.get("title", "Untitled")[:200]
    content      = data.get("content", "")
    content_type = data.get("content_type", "notes")
    word_count   = len(content.split())
    db = SessionLocal()
    try:
        item = SavedContent(
            user_id=session["user_id"],
            title=title,
            content_type=content_type,
            content=content,
            word_count=word_count
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return jsonify({"success": True, "id": item.id, "title": title})
    finally:
        db.close()

@library_bp.route("/api/library/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    db = SessionLocal()
    try:
        item = db.query(SavedContent).filter_by(
            id=item_id, user_id=session["user_id"]
        ).first()
        if not item:
            return jsonify({"error": "Not found"}), 404
        db.delete(item)
        db.commit()
        return jsonify({"success": True})
    finally:
        db.close()
