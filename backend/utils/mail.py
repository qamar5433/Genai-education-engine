"""
backend/utils/mail.py
─────────────────────
Brevo REST API email utility for GENAI EDUCATION ENGINE.
Uses the /v3/smtp/email transactional email endpoint.

Required environment variables:
  BREVO_API_KEY       – your Brevo API key  (starts with xkeysib-...)
  BREVO_SENDER_EMAIL  – a verified sender email in your Brevo account
  BREVO_SENDER_NAME   – display name (optional, defaults to APP_NAME)
"""

import os
import threading
import requests

# ─────────────────────────── Config ─────────────────────────────────────────

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
APP_NAME      = "GENAI EDUCATION ENGINE"


def _get_config():
    """Return Brevo config dict from env vars, or None if not configured."""
    api_key      = os.environ.get("BREVO_API_KEY", "").strip()
    sender_email = os.environ.get("BREVO_SENDER_EMAIL", "").strip()
    sender_name  = os.environ.get("BREVO_SENDER_NAME", APP_NAME).strip()
    if api_key and sender_email:
        return {"api_key": api_key, "sender_email": sender_email, "sender_name": sender_name}
    return None


def is_email_enabled() -> bool:
    """Returns True when Brevo API credentials are fully configured."""
    return _get_config() is not None


# ─────────────────────────── HTML Templates ──────────────────────────────────

def _build_otp_html(otp_code: str, purpose: str = "Email Verification") -> str:
    """Returns a branded HTML email body for OTP emails."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>{purpose}</title>
</head>
<body style="margin:0;padding:0;background:#0f0f1a;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0"
         style="background:#0f0f1a;padding:40px 20px;">
    <tr><td align="center">
      <table width="580" cellpadding="0" cellspacing="0"
             style="background:linear-gradient(135deg,#1a1a2e,#16213e);
                    border-radius:16px;border:1px solid rgba(71,70,229,0.25);
                    box-shadow:0 20px 60px rgba(0,0,0,0.5);overflow:hidden;">
        <!-- Header -->
        <tr>
          <td align="center"
              style="background:linear-gradient(135deg,#4746E5,#7c3aed);
                     padding:30px 40px;">
            <h1 style="margin:0;color:#fff;font-size:20px;font-weight:800;
                        letter-spacing:.5px;">{APP_NAME}</h1>
            <p style="margin:6px 0 0;color:rgba(255,255,255,.7);font-size:12px;">
              AI-Powered Learning Platform
            </p>
          </td>
        </tr>
        <!-- Body -->
        <tr>
          <td style="padding:36px 40px;">
            <h2 style="margin:0 0 14px;color:#e2e8f0;font-size:18px;font-weight:700;">
              {purpose}
            </h2>
            <p style="margin:0 0 24px;color:#94a3b8;font-size:15px;line-height:1.6;">
              Use the one-time code below to complete your request.
              This code is valid for
              <strong style="color:#e2e8f0;">5 minutes</strong>
              and can only be used once.
            </p>
            <!-- OTP Box -->
            <div style="background:rgba(71,70,229,.08);
                        border:1px solid rgba(71,70,229,.3);
                        border-radius:12px;padding:24px;
                        text-align:center;margin-bottom:24px;">
              <p style="margin:0 0 6px;color:#94a3b8;font-size:11px;
                         text-transform:uppercase;letter-spacing:1.5px;">
                Your One-Time Code
              </p>
              <span style="font-size:38px;font-weight:900;letter-spacing:10px;
                           color:#fff;font-family:'Courier New',monospace;">
                {otp_code}
              </span>
            </div>
            <p style="margin:0;color:#64748b;font-size:13px;line-height:1.5;">
              If you did not request this, you can safely ignore this email.
              Your account remains secure.
            </p>
          </td>
        </tr>
        <!-- Footer -->
        <tr>
          <td style="padding:18px 40px;
                     border-top:1px solid rgba(255,255,255,.06);">
            <p style="margin:0;color:#475569;font-size:11px;text-align:center;">
              &copy; 2025 {APP_NAME} &middot; Automated message &mdash; please do not reply.
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


# ─────────────────────────── Core Sender ─────────────────────────────────────

def _send_email(to_email: str, subject: str, html_body: str) -> tuple:
    """
    Send an email via Brevo REST API.
    Returns (success: bool, message: str).
    """
    cfg = _get_config()
    if not cfg:
        return False, (
            "BREVO_API_KEY or BREVO_SENDER_EMAIL not set in environment. "
            "Add them to your .env file."
        )

    headers = {
        "api-key":      cfg["api_key"],
        "Content-Type": "application/json",
        "Accept":       "application/json",
    }
    payload = {
        "sender":      {"name": cfg["sender_name"], "email": cfg["sender_email"]},
        "to":          [{"email": to_email}],
        "subject":     subject,
        "htmlContent": html_body,
    }

    try:
        resp = requests.post(BREVO_API_URL, json=payload, headers=headers, timeout=15)
        if resp.status_code in (200, 201):
            return True, "Email sent successfully."

        # Parse error from Brevo
        try:
            err = resp.json()
        except Exception:
            err = {}
        code    = err.get("code", "")
        message = err.get("message", resp.text or "Unknown error")

        # Helpful hints for common errors
        if code == "unauthorized":
            hint = (
                "API key unauthorized. Go to https://app.brevo.com/security/authorised_ips "
                "and whitelist your server IP, or disable IP restriction."
            )
            return False, hint
        if code == "invalid_parameter" and "sender" in message.lower():
            hint = (
                "Sender email not verified in Brevo. "
                "Go to https://app.brevo.com/senders and add/verify your sender email, "
                "then update BREVO_SENDER_EMAIL in .env."
            )
            return False, hint

        return False, f"Brevo API error [{resp.status_code}] {code}: {message}"

    except requests.exceptions.Timeout:
        return False, "Request to Brevo timed out. Check your internet connection."
    except requests.exceptions.ConnectionError as e:
        return False, f"Could not reach Brevo API: {e}"
    except Exception as e:
        return False, f"Unexpected error: {e}"


# ─────────────────────────── Public API ──────────────────────────────────────

def send_otp_email_sync(to_email: str, otp_code: str) -> tuple:
    """Send email-verification OTP. Returns (success, message)."""
    subject = f"Your Verification Code – {APP_NAME}"
    html    = _build_otp_html(otp_code, purpose="Email Verification")
    return _send_email(to_email, subject, html)


def send_reset_otp_email_sync(to_email: str, otp_code: str) -> tuple:
    """Send password-reset OTP. Returns (success, message)."""
    subject = f"Password Reset Code – {APP_NAME}"
    html    = _build_otp_html(otp_code, purpose="Password Reset")
    return _send_email(to_email, subject, html)


def send_otp_email_async(to_email: str, otp_code: str) -> None:
    """Non-blocking wrapper for send_otp_email_sync."""
    t = threading.Thread(
        target=send_otp_email_sync, args=(to_email, otp_code), daemon=True
    )
    t.start()


def send_reset_otp_email_async(to_email: str, otp_code: str) -> None:
    """Non-blocking wrapper for send_reset_otp_email_sync."""
    t = threading.Thread(
        target=send_reset_otp_email_sync, args=(to_email, otp_code), daemon=True
    )
    t.start()
