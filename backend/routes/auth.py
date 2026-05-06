"""
backend/routes/auth.py
──────────────────────
Authentication routes for GENAI EDUCATION ENGINE.

Endpoints:
  POST /api/auth/signup          – Register new user, send verification OTP
  POST /api/auth/login           – Login (blocks unverified users)
  POST /api/auth/logout          – Clear session
  GET  /api/auth/me              – Return current session user
  POST /api/auth/verify-otp      – Verify email OTP after signup
  POST /api/auth/resend-otp      – Resend verification OTP (60-sec cooldown)
  POST /api/auth/forgot-password – Send password-reset OTP
  POST /api/auth/verify-reset-otp – Verify reset OTP
  POST /api/auth/reset-password  – Set new password after OTP verified
"""

import os
import sys
import random
from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify, session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bcrypt
from database import SessionLocal
from models import User
from utils.mail import (
    send_otp_email_sync,
    send_otp_email_async,
    send_reset_otp_email_sync,
    send_reset_otp_email_async,
    is_email_enabled,
)

auth_bp = Blueprint("auth", __name__)

# ─── Constants ───────────────────────────────────────────────────────────────

OTP_EXPIRY_MINUTES   = 5    # how long OTPs stay valid
RESEND_COOLDOWN_SECS = 60   # minimum seconds between resend requests


def _generate_otp() -> str:
    """Generate a secure 6-digit OTP string."""
    return f"{random.randint(100000, 999999)}"


def _otp_expiry() -> datetime:
    """Return UTC expiry timestamp (now + OTP_EXPIRY_MINUTES)."""
    return datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)


def _resend_cooldown_remaining(user: User) -> int:
    """
    Return seconds remaining in the resend cooldown, or 0 if cooldown is over.
    """
    if not user.otp_resend_at:
        return 0
    elapsed = (datetime.utcnow() - user.otp_resend_at).total_seconds()
    remaining = RESEND_COOLDOWN_SECS - int(elapsed)
    return max(0, remaining)


# ─── Signup ──────────────────────────────────────────────────────────────────

@auth_bp.route("/api/auth/signup", methods=["POST"])
def signup():
    """
    Register a new user.
    - If email is already registered but unverified: resend OTP.
    - If email is already registered and verified: reject.
    - Otherwise: create user, send OTP, require verification.
    - If Brevo not configured: auto-verify (dev mode).
    """
    data     = request.get_json(force=True)
    name     = data.get("name",     "").strip()
    email    = data.get("email",    "").strip().lower()
    password = data.get("password", "")

    # ── Validation ──────────────────────────────────────────────────────────
    if not name or not email or not password:
        return jsonify({"error": "All fields are required."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400

    db = SessionLocal()
    try:
        existing = db.query(User).filter_by(email=email).first()

        # Already registered
        if existing:
            if not existing.is_verified:
                # Check cooldown before resending
                wait = _resend_cooldown_remaining(existing)
                if wait > 0:
                    return jsonify({
                        "error": f"Please wait {wait} seconds before requesting another code.",
                        "cooldown_remaining": wait
                    }), 429

                # Resend fresh OTP
                otp = _generate_otp()
                existing.otp_code       = otp
                existing.otp_expires_at = _otp_expiry()
                existing.otp_resend_at  = datetime.utcnow()
                db.commit()

                success, _ = send_otp_email_sync(email, otp)
                response = {
                    "message": "Email already registered but not verified. A new code has been sent.",
                    "requires_verification": True,
                    "email": email,
                }
                if not success:
                    response["dev_otp"] = otp   # show in response if email fails
                return jsonify(response), 200

            return jsonify({"error": "This email is already registered. Please log in."}), 409

        # ── New user ─────────────────────────────────────────────────────────
        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        otp     = _generate_otp()
        email_on = is_email_enabled()

        user = User(
            name=name,
            email=email,
            password_hash=pw_hash,
            is_verified=not email_on,           # auto-verify when email not configured
            otp_code=otp if email_on else None,
            otp_expires_at=_otp_expiry() if email_on else None,
            otp_resend_at=datetime.utcnow() if email_on else None,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Dev mode (no Brevo configured) → log in immediately
        if not email_on:
            session["user_id"]   = user.id
            session["user_name"] = user.name
            return jsonify({
                "message": "Account created. (Email verification disabled — Brevo not configured)",
                "requires_verification": False,
                "email": email,
                "user": {"id": user.id, "name": user.name, "email": user.email},
            }), 201

        # Send OTP asynchronously so response is fast
        send_otp_email_async(email, otp)

        return jsonify({
            "message": "Account created. Please verify your email.",
            "requires_verification": True,
            "email": email,
        }), 201

    finally:
        db.close()


# ─── Login ───────────────────────────────────────────────────────────────────

@auth_bp.route("/api/auth/login", methods=["POST"])
def login():
    """
    Log in an existing user.
    - Rejects login if email is not yet verified.
    - Sends a fresh OTP to unverified users.
    """
    data     = request.get_json(force=True)
    email    = data.get("email",    "").strip().lower()
    password = data.get("password", "")

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(email=email).first()
        if not user or not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
            return jsonify({"error": "Invalid email or password."}), 401

        # Block unverified users and send a fresh OTP
        if not user.is_verified:
            wait = _resend_cooldown_remaining(user)
            if wait == 0:
                # Safe to send a new OTP
                otp = _generate_otp()
                user.otp_code       = otp
                user.otp_expires_at = _otp_expiry()
                user.otp_resend_at  = datetime.utcnow()
                db.commit()
                send_otp_email_async(email, otp)

            return jsonify({
                "error": "Email not verified. A verification code has been sent.",
                "requires_verification": True,
                "email": email,
            }), 403

        session["user_id"]   = user.id
        session["user_name"] = user.name
        return jsonify({
            "message": "Login successful",
            "user": {
                "id":     user.id,
                "name":   user.name,
                "email":  user.email,
                "xp":     user.xp,
                "streak": user.streak,
                "level":  user.level,
            },
        }), 200

    finally:
        db.close()


# ─── Logout ──────────────────────────────────────────────────────────────────

@auth_bp.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully."}), 200


# ─── Me ──────────────────────────────────────────────────────────────────────

@auth_bp.route("/api/auth/me", methods=["GET"])
def me():
    uid = session.get("user_id")
    if not uid:
        return jsonify({"error": "Not authenticated."}), 401
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(id=uid).first()
        if not user:
            return jsonify({"error": "User not found."}), 404
        return jsonify({
            "id":     user.id,
            "name":   user.name,
            "email":  user.email,
            "xp":     user.xp,
            "streak": user.streak,
            "level":  user.level,
        }), 200
    finally:
        db.close()


# ─── Verify OTP ──────────────────────────────────────────────────────────────

@auth_bp.route("/api/auth/verify-otp", methods=["POST"])
def verify_otp():
    """Verify the 6-digit email-verification OTP sent at signup."""
    data     = request.get_json(force=True)
    email    = data.get("email", "").strip().lower()
    otp_code = data.get("otp",   "").strip()

    if not email or not otp_code:
        return jsonify({"error": "Email and OTP are required."}), 400

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(email=email).first()
        if not user:
            return jsonify({"error": "No account found for this email."}), 404

        if user.is_verified:
            # Already verified — just log them in
            session["user_id"]   = user.id
            session["user_name"] = user.name
            return jsonify({
                "message": "Already verified.",
                "user": {"id": user.id, "name": user.name, "email": user.email},
            }), 200

        # Check OTP expiry first (better UX than wrong-OTP message for expired codes)
        if not user.otp_expires_at or user.otp_expires_at < datetime.utcnow():
            return jsonify({
                "error": f"OTP has expired. Please request a new one (valid for {OTP_EXPIRY_MINUTES} min)."
            }), 401

        if user.otp_code != otp_code:
            return jsonify({"error": "Invalid OTP code. Please try again."}), 401

        # ── Success ──────────────────────────────────────────────────────────
        user.is_verified    = True
        user.otp_code       = None
        user.otp_expires_at = None
        user.otp_resend_at  = None
        db.commit()

        session["user_id"]   = user.id
        session["user_name"] = user.name

        return jsonify({
            "message": "Email verified successfully!",
            "user": {"id": user.id, "name": user.name, "email": user.email},
        }), 200

    finally:
        db.close()


# ─── Resend OTP ──────────────────────────────────────────────────────────────

@auth_bp.route("/api/auth/resend-otp", methods=["POST"])
def resend_otp():
    """
    Resend the email-verification OTP.
    Enforces a 60-second cooldown to prevent abuse.
    """
    data  = request.get_json(force=True)
    email = data.get("email", "").strip().lower()

    if not email:
        return jsonify({"error": "Email is required."}), 400

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(email=email).first()
        if not user:
            return jsonify({"error": "No account found for this email."}), 404

        if user.is_verified:
            return jsonify({"error": "This account is already verified."}), 400

        # Cooldown check
        wait = _resend_cooldown_remaining(user)
        if wait > 0:
            return jsonify({
                "error": f"Please wait {wait} seconds before requesting another code.",
                "cooldown_remaining": wait,
            }), 429

        # Send new OTP
        otp = _generate_otp()
        user.otp_code       = otp
        user.otp_expires_at = _otp_expiry()
        user.otp_resend_at  = datetime.utcnow()
        db.commit()

        success, err_msg = send_otp_email_sync(email, otp)

        response = {"message": "A new verification code has been sent to your email."}
        if not success:
            # If email fails, we log it server-side but do NOT leak it to the user.
            print(f"FAILED TO SEND OTP TO {email}: {err_msg}")
            return jsonify({"error": "Failed to send verification email. Please check server configuration."}), 500

        return jsonify(response), 200

    finally:
        db.close()


# ─── Forgot Password ─────────────────────────────────────────────────────────

@auth_bp.route("/api/auth/forgot-password", methods=["POST"])
def forgot_password():
    """
    Step 1 of password reset: generate a reset OTP and email it.
    Always returns 200 even if email not found (prevents user enumeration).
    """
    data  = request.get_json(force=True)
    email = data.get("email", "").strip().lower()

    if not email:
        return jsonify({"error": "Email is required."}), 400

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(email=email).first()

        # Return 200 regardless to avoid email enumeration
        if not user:
            return jsonify({
                "message": "If an account exists for this email, a reset code has been sent."
            }), 200

        # Enforce resend cooldown for reset OTPs too
        wait = _resend_cooldown_remaining(user)
        if wait > 0:
            return jsonify({
                "error": f"Please wait {wait} seconds before requesting another code.",
                "cooldown_remaining": wait,
            }), 429

        otp = _generate_otp()
        user.reset_otp            = otp
        user.reset_otp_expires_at = _otp_expiry()
        user.otp_resend_at        = datetime.utcnow()   # shared cooldown field
        db.commit()

        success, err_msg = send_reset_otp_email_sync(email, otp)

        response = {
            "message": "If an account exists for this email, a reset code has been sent.",
            "email":   email,
        }
        if not success:
            print(f"FAILED TO SEND RESET OTP TO {email}: {err_msg}")
            # We still return 200 to prevent user enumeration, but it won't have dev_otp
        
        return jsonify(response), 200

    finally:
        db.close()


# ─── Verify Reset OTP ────────────────────────────────────────────────────────

@auth_bp.route("/api/auth/verify-reset-otp", methods=["POST"])
def verify_reset_otp():
    """
    Step 2 of password reset: verify the reset OTP.
    On success, marks the OTP as consumed and allows the client to
    call /api/auth/reset-password.
    Returns a short-lived 'reset_token' (the verified OTP reused as token).
    """
    data     = request.get_json(force=True)
    email    = data.get("email",    "").strip().lower()
    otp_code = data.get("otp",      "").strip()

    if not email or not otp_code:
        return jsonify({"error": "Email and OTP are required."}), 400

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(email=email).first()
        if not user:
            return jsonify({"error": "No account found for this email."}), 404

        if not user.reset_otp:
            return jsonify({"error": "No password reset was requested for this account."}), 400

        if not user.reset_otp_expires_at or user.reset_otp_expires_at < datetime.utcnow():
            return jsonify({
                "error": f"Reset code has expired. Please request a new one."
            }), 401

        if user.reset_otp != otp_code:
            return jsonify({"error": "Invalid reset code. Please try again."}), 401

        # Store a server-side flag in session so reset-password can be called
        session["reset_email"] = email

        # Clear the OTP (one-time use)
        user.reset_otp            = None
        user.reset_otp_expires_at = None
        db.commit()

        return jsonify({
            "message": "Reset code verified. You may now set a new password.",
            "email":   email,
        }), 200

    finally:
        db.close()


# ─── Reset Password ──────────────────────────────────────────────────────────

@auth_bp.route("/api/auth/reset-password", methods=["POST"])
def reset_password():
    """
    Step 3 of password reset: set a new password.
    Requires verify-reset-otp to have been called in the same session first.
    """
    data         = request.get_json(force=True)
    email        = data.get("email",        "").strip().lower()
    new_password = data.get("new_password", "")

    if not email or not new_password:
        return jsonify({"error": "Email and new password are required."}), 400

    if len(new_password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400

    # Verify the session token set by verify-reset-otp
    reset_email = session.get("reset_email", "")
    if reset_email != email:
        return jsonify({
            "error": "Reset session invalid or expired. Please start over."
        }), 403

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(email=email).first()
        if not user:
            return jsonify({"error": "No account found for this email."}), 404

        user.password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        # Ensure the account is marked verified (edge case: reset before verification)
        user.is_verified   = True
        db.commit()

        # Clear the reset session key
        session.pop("reset_email", None)

        return jsonify({
            "message": "Password reset successfully. You can now log in."
        }), 200

    finally:
        db.close()
