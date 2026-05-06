import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
load_dotenv()
from database import init_db

app = Flask(__name__, static_folder=None)

# Use env var in production, fallback for local dev
app.secret_key = os.environ.get("SECRET_KEY", "quizgenius-local-dev-key-change-in-prod")
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("RENDER", False)  # HTTPS on Render

# Allow any origin in production (Render serves frontend from same domain)
CORS(app, supports_credentials=True, origins="*")

# Register blueprints
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.quiz import quiz_bp
from routes.tutor import tutor_bp
from routes.analytics import analytics_bp
from routes.leaderboard import leaderboard_bp
from routes.content import content_bp
from routes.profile import profile_bp
from routes.flashcards import flashcards_bp
from routes.progress import progress_bp
from routes.library import library_bp
from routes.achievements import achievements_bp
from routes.notifications import notifications_bp
from routes.upload import upload_bp
from routes.mindmap import mindmap_bp
from routes.courses import courses_bp

app.register_blueprint(mindmap_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(quiz_bp)
app.register_blueprint(tutor_bp)
app.register_blueprint(analytics_bp)
app.register_blueprint(leaderboard_bp)
app.register_blueprint(content_bp)
app.register_blueprint(profile_bp)
app.register_blueprint(flashcards_bp)
app.register_blueprint(progress_bp)
app.register_blueprint(library_bp)
app.register_blueprint(achievements_bp)
app.register_blueprint(notifications_bp)
app.register_blueprint(upload_bp)
app.register_blueprint(courses_bp)

# Serve frontend static files
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")

@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(FRONTEND_DIR, filename)

@app.route("/api/health", methods=["GET"])
def health():
    return {"status": "ok", "message": "GENAI EDUCATION ENGINE API running"}, 200

# Initialize DB on startup
with app.app_context():
    init_db()
    from database import SessionLocal
    from seed import ensure_courses
    db = SessionLocal()
    try:
        ensure_courses(db)
    finally:
        db.close()

if __name__ == "__main__":
    print("GENAI EDUCANTION ENGINE server starting...")
    print("Open: http://localhost:5000")
    app.run(debug=True, port=5000, host="0.0.0.0")
