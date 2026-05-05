from flask import Blueprint, jsonify, request, session, Response, stream_with_context
import json
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import SessionLocal
from models import TutorSession, TutorMessage, User
from datetime import datetime

tutor_bp = Blueprint("tutor", __name__)

@tutor_bp.route("/api/tutor/session", methods=["POST"])
def start_session():
    uid = session.get("user_id")
    if not uid:
        return jsonify({"error": "Not authenticated"}), 401
    db = SessionLocal()
    try:
        ts = TutorSession(user_id=uid)
        db.add(ts)
        db.commit()
        db.refresh(ts)
        welcome = TutorMessage(
            session_id=ts.id, role="ai",
            content="Hello! I'm your **GENAI EDUCANTION ENGINE Tutor** 🤖\n\nI'm powered by GPT-4 and here 24/7 to help you master any subject — math, science, programming, history, and more.\n\n**How can I help you today?** Ask me to:\n- Explain a concept step by step\n- Solve a problem with you\n- Quiz you on a topic\n- Break down a difficult theory\n\nWhat are you studying? 📚"
        )
        db.add(welcome)
        db.commit()
        return jsonify({"session_id": ts.id}), 201
    finally:
        db.close()

@tutor_bp.route("/api/tutor/chat", methods=["POST"])
def chat():
    uid = session.get("user_id")
    if not uid:
        return jsonify({"error": "Not authenticated"}), 401
    data       = request.get_json()
    session_id = data.get("session_id")
    message    = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "Message required"}), 400

    db = SessionLocal()
    try:
        ts = db.query(TutorSession).filter_by(id=session_id, user_id=uid).first()
        if not ts:
            return jsonify({"error": "Session not found"}), 404

        # Fetch conversation history for context
        history = db.query(TutorMessage).filter_by(session_id=session_id)\
                    .order_by(TutorMessage.created_at).all()
        history_dicts = [{"role": m.role, "content": m.content} for m in history]

        # Save user message
        user_msg = TutorMessage(session_id=session_id, role="user", content=message)
        db.add(user_msg)

        # Get real GPT response
        try:
            from ai_client import get_tutor_response
            ai_text = get_tutor_response(message, history_dicts)
        except Exception as e:
            # Fallback: intelligent keyword-based responses
            msg_lower = message.lower()
            import random
            fallbacks = {
                "quantum": "Great question about quantum mechanics! The **wave-particle duality** means particles like electrons behave as waves until measured. The famous double-slit experiment shows interference patterns — a wave phenomenon — yet particles land one at a time. The **wave function ψ** describes the *probability* of finding a particle at a given location. What aspect would you like to explore further?",
                "calculus": "In calculus, **derivatives** measure the rate of change at a point, while **integrals** measure accumulated quantity. For partial derivatives, treat all variables except the target as constants. For ∂f/∂x of f(x,y) = 3x²y, just differentiate with respect to x → **6xy**. What specific concept are you working on?",
                "machine learning": "Machine learning is broadly split into **supervised** (labeled data → predict labels), **unsupervised** (find hidden patterns), and **reinforcement learning** (learn from rewards). The classic issue is **bias-variance tradeoff** — complex models overfit (low bias, high variance), simple ones underfit. What aspect of ML would you like to dive into?",
                "python": "Python is powerful for data science via libraries like **NumPy**, **Pandas**, and **scikit-learn**. Key patterns: use `df.groupby()` for aggregations, `.apply()` for custom row functions, and list comprehensions for clean transformations. What Python concept can I help you with?",
            }
            response = next((v for k, v in fallbacks.items() if k in msg_lower),
                            "That's a great question! Let me break it down step by step. Could you share what specific aspect you're most curious about? That way I can tailor my explanation to exactly what will help you most.")
            ai_text = response + f"\n\n*(Note: AI temporarily using cached response — {str(e)[:60]})*"

        ai_msg = TutorMessage(session_id=session_id, role="ai", content=ai_text)
        db.add(ai_msg)
        db.commit()
        return jsonify({"response": ai_text}), 200
    finally:
        db.close()

@tutor_bp.route("/api/tutor/chat_stream", methods=["POST"])
def chat_stream():
    uid = session.get("user_id")
    if not uid:
        return jsonify({"error": "Not authenticated"}), 401
    data       = request.get_json()
    session_id = data.get("session_id")
    message    = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "Message required"}), 400

    db = SessionLocal()
    try:
        ts = db.query(TutorSession).filter_by(id=session_id, user_id=uid).first()
        if not ts:
            return jsonify({"error": "Session not found"}), 404

        # Fetch conversation history for context
        history = db.query(TutorMessage).filter_by(session_id=session_id)\
                    .order_by(TutorMessage.created_at).all()
        history_dicts = [{"role": m.role, "content": m.content} for m in history]

        # Save user message
        user_msg = TutorMessage(session_id=session_id, role="user", content=message)
        db.add(user_msg)
        db.commit()
    finally:
        db.close()

    def generate():
        ai_text = ""
        try:
            from ai_client import get_tutor_response_stream
            for token in get_tutor_response_stream(message, history_dicts):
                ai_text += token
                yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception as e:
            fallback = "I'm having trouble connecting to my AI brain right now. Please try again later."
            ai_text = fallback + f"\n\n*(Error: {str(e)[:60]})*"
            yield f"data: {json.dumps({'token': ai_text})}\n\n"
        
        yield "data: [DONE]\n\n"

        # Save ai_msg to db after stream completes
        db_save = SessionLocal()
        try:
            ai_msg = TutorMessage(session_id=session_id, role="ai", content=ai_text)
            db_save.add(ai_msg)
            db_save.commit()
        finally:
            db_save.close()

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@tutor_bp.route("/api/tutor/history/<int:session_id>", methods=["GET"])
def history(session_id):
    uid = session.get("user_id")
    if not uid:
        return jsonify({"error": "Not authenticated"}), 401
    db = SessionLocal()
    try:
        messages = db.query(TutorMessage).filter_by(session_id=session_id)\
                     .order_by(TutorMessage.created_at).all()
        return jsonify({"messages": [
            {"role": m.role, "content": m.content, "time": m.created_at.strftime("%H:%M")}
            for m in messages
        ]}), 200
    finally:
        db.close()
