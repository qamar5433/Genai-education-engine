import smtplib
import os
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_otp_email_sync(to_email, otp_code):
    gmail_user = os.environ.get("GMAIL_USER")
    gmail_password_raw = os.environ.get("GMAIL_APP_PASSWORD")
    
    if not gmail_user or not gmail_password_raw:
        return False, "GMAIL_USER or GMAIL_APP_PASSWORD not set in .env"
        
    gmail_password = gmail_password_raw.replace(" ", "")

    subject = "Verify your account - GENAI EDUCATION ENGINE"
    
    html = f"""
    <html>
      <body style="font-family: 'Inter', sans-serif; background-color: #f4f4f5; padding: 20px; text-align: center;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 40px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
          <h1 style="color: #4f46e5; margin-bottom: 10px;">GENAI EDUCATION ENGINE</h1>
          <h2 style="color: #1f2937; font-weight: 600;">Email Verification</h2>
          <p style="color: #4b5563; font-size: 16px; margin-bottom: 30px;">
            Thank you for signing up! Use the following One-Time Password (OTP) to verify your email address and activate your account.
          </p>
          <div style="background-color: #f3f4f6; padding: 20px; border-radius: 8px; margin-bottom: 30px;">
            <span style="font-size: 32px; font-weight: 800; letter-spacing: 5px; color: #111827;">{otp_code}</span>
          </div>
          <p style="color: #6b7280; font-size: 14px;">
            This OTP is valid for 10 minutes. If you did not request this, please ignore this email.
          </p>
        </div>
      </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"GENAI EDUCATION ENGINE <{gmail_user}>"
    msg["To"] = to_email

    msg.attach(MIMEText(html, "html"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.login(gmail_user, gmail_password)
        server.sendmail(gmail_user, to_email, msg.as_string())
        server.close()
        return True, "Email sent successfully"
    except smtplib.SMTPAuthenticationError:
        return False, "Invalid Gmail credentials. Ensure you are using a 16-character App Password."
    except Exception as e:
        return False, str(e)

def send_otp_email_async(to_email, otp_code):
    thread = threading.Thread(target=send_otp_email_sync, args=(to_email, otp_code))
    thread.daemon = True
    thread.start()
