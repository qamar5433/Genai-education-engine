from flask import Blueprint, request, jsonify, session
import bcrypt
import sys, os
import random
from datetime import datetime, timedelta
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import SessionLocal
from models import User
from utils.mail import send_otp_email_sync, send_otp_email_async

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/api/auth/signup", methods=["POST"])
def signup():
    data = request.get_json()
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    if not name or not email or not password:
        return jsonify({"error": "All fields required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    db = SessionLocal()
    try:
        existing_user = db.query(User).filter_by(email=email).first()
        if existing_user:
            if not existing_user.is_verified:
                # If not verified, allow them to go to OTP screen
                otp_code = f"{random.randint(100000, 999999)}"
                existing_user.otp_code = otp_code
                existing_user.otp_expires_at = datetime.utcnow() + timedelta(minutes=10)
                success, _ = send_otp_email_sync(email, otp_code)
                db.commit()
                return jsonify({
                    "message": "Email already registered but not verified. A new code has been sent.",
                    "requires_verification": True,
                    "email": email
                }), 200
            return jsonify({"error": "Email already registered"}), 409
        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        otp_code = f"{random.randint(100000, 999999)}"
        otp_expires_at = datetime.utcnow() + timedelta(minutes=10)
        
        gmail_user = os.environ.get("GMAIL_USER")
        email_enabled = bool(gmail_user and gmail_user != "your_email@gmail.com")
        
        user = User(
            name=name, 
            email=email, 
            password_hash=pw_hash, 
            is_verified=not email_enabled,
            otp_code=otp_code if email_enabled else None,
            otp_expires_at=otp_expires_at if email_enabled else None
        )
        db.add(user)
        
        if email_enabled:
            send_otp_email_async(email, otp_code)
            success = True
            err_msg = ""
        
        db.commit()
        db.refresh(user)
        
        if not email_enabled:
            session["user_id"] = user.id
            session["user_name"] = user.name
            return jsonify({"message": "Account created. (Email verification disabled)", "requires_verification": False, "email": email, "user": {"id": user.id, "name": user.name, "email": user.email}}), 201
        
        response_data = {
            "message": "Account created. Please verify your email.", 
            "requires_verification": True, 
            "email": email
        }
        
        # If email fails, fallback to showing it on screen so the user isn't blocked
        if not success:
            response_data["dev_otp"] = otp_code
            response_data["email_error"] = err_msg
            
        return jsonify(response_data), 201
    finally:
        db.close()

@auth_bp.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(email=email).first()
        if not user or not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
            return jsonify({"error": "Invalid email or password"}), 401
            
        if not user.is_verified:
            # Send a new OTP and inform them
            otp_code = f"{random.randint(100000, 999999)}"
            user.otp_code = otp_code
            user.otp_expires_at = datetime.utcnow() + timedelta(minutes=10)
            send_otp_email_sync(email, otp_code) # Send sync for simplicity here
            db.commit()
            return jsonify({
                "error": "Email not verified", 
                "requires_verification": True, 
                "email": email
            }), 403

        session["user_id"] = user.id
        session["user_name"] = user.name
        return jsonify({"message": "Login successful", "user": {"id": user.id, "name": user.name, "email": user.email, "xp": user.xp, "streak": user.streak, "level": user.level}}), 200
    finally:
        db.close()

@auth_bp.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"}), 200

@auth_bp.route("/api/auth/me", methods=["GET"])
def me():
    uid = session.get("user_id")
    if not uid:
        return jsonify({"error": "Not authenticated"}), 401
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(id=uid).first()
        if not user:
            return jsonify({"error": "User not found"}), 404
        return jsonify({"id": user.id, "name": user.name, "email": user.email, "xp": user.xp, "streak": user.streak, "level": user.level}), 200
    finally:
        db.close()

@auth_bp.route("/api/auth/verify-otp", methods=["POST"])
def verify_otp():
    data = request.get_json()
    email = data.get("email", "").strip().lower()
    otp_code = data.get("otp", "").strip()
    
    if not email or not otp_code:
        return jsonify({"error": "Email and OTP required"}), 400
        
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(email=email).first()
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        if user.is_verified:
            return jsonify({"error": "User is already verified"}), 400
            
        if user.otp_code != otp_code:
            return jsonify({"error": "Invalid OTP code"}), 401
            
        if not user.otp_expires_at or user.otp_expires_at < datetime.utcnow():
            return jsonify({"error": "OTP has expired. Please request a new one."}), 401
            
        # Verify success
        user.is_verified = True
        user.otp_code = None
        user.otp_expires_at = None
        db.commit()
        
        session["user_id"] = user.id
        session["user_name"] = user.name
        
        return jsonify({"message": "Verification successful", "user": {"id": user.id, "name": user.name, "email": user.email}}), 200
    finally:
        db.close()

@auth_bp.route("/api/auth/resend-otp", methods=["POST"])
def resend_otp():
    data = request.get_json()
    email = data.get("email", "").strip().lower()
    
    if not email:
        return jsonify({"error": "Email required"}), 400
        
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(email=email).first()
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        if user.is_verified:
            return jsonify({"error": "User is already verified"}), 400
            
        # Generate new OTP
        otp_code = f"{random.randint(100000, 999999)}"
        user.otp_code = otp_code
        user.otp_expires_at = datetime.utcnow() + timedelta(minutes=10)
        
        success, err_msg = send_otp_email_sync(email, otp_code)
        db.commit()
        
        response_data = {"message": "OTP resent successfully"}
        if not success:
            response_data["dev_otp"] = otp_code
            
        return jsonify(response_data), 200
    finally:
        db.close()
