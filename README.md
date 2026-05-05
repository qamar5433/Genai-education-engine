# 🎓 GENAI EDUCANTION ENGINE

An AI-powered full-stack learning platform built with **Flask** (Python backend) and **Vanilla HTML/CSS/JS** (frontend). Features AI-generated quizzes, study notes, flashcards, mind maps, an AI tutor, analytics, and more.

---

## 🚀 Quick Start (Local)

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/genai-education-engine.git
cd genai-education-engine
```

### 2. Create a virtual environment
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up environment variables
```bash
cp .env.example .env
# Edit .env and fill in your API keys
```

### 5. Run the server
```bash
python backend/app.py
```

Open [http://localhost:5000](http://localhost:5000) in your browser.

**Demo login:** `alex@demo.com` / `password123`

---

## ☁️ Deploy to Render

### Option A — One-Click Blueprint (Recommended)
1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → **New** → **Blueprint**
3. Connect your GitHub repo — Render will auto-detect `render.yaml`
4. Set your environment variables in the Render dashboard:
   - `OPENAI_API_KEY` or `GOOGLE_API_KEY`
   - `GMAIL_USER` and `GMAIL_APP_PASSWORD`
5. Click **Deploy**

### Option B — Manual Web Service
1. Render → **New Web Service** → Connect GitHub repo
2. **Runtime:** Python
3. **Build Command:** `pip install -r requirements.txt`
4. **Start Command:** `gunicorn --chdir backend app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
5. Add environment variables from `.env.example`

---

## 🏗️ Project Structure

```
genai-education-engine/
├── backend/
│   ├── app.py              # Flask entry point
│   ├── database.py         # SQLAlchemy setup
│   ├── models.py           # DB models
│   ├── ai_client.py        # AI API integration
│   └── routes/             # API blueprints
│       ├── auth.py
│       ├── quiz.py
│       ├── tutor.py
│       └── ...
├── frontend/
│   ├── index.html          # Landing page
│   ├── dashboard.html
│   ├── css/main.css        # Global design system
│   ├── js/                 # JS modules
│   └── img/                # Static assets (logo etc.)
├── requirements.txt
├── Procfile
├── render.yaml
└── .env.example
```

---

## 🔑 Environment Variables

| Variable | Description | Required |
|---|---|---|
| `SECRET_KEY` | Flask session secret | Yes (auto-generated on Render) |
| `OPENAI_API_KEY` | OpenAI GPT-4o key | Yes (or Google) |
| `GOOGLE_API_KEY` | Gemini API key | Yes (or OpenAI) |
| `GMAIL_USER` | Gmail address for OTP emails | Optional |
| `GMAIL_APP_PASSWORD` | Gmail App Password | Optional |

---

## ✨ Features

- 🤖 **AI Quiz Generation** — GPT-4o powered, course-specific
- 📚 **AI Study Notes** — Read notes before quizzes
- 🧠 **AI Tutor** — Real-time chat with subject specialist
- 🗺️ **Mind Maps** — Visual concept mapping
- 🃏 **Flashcards** — Spaced repetition system
- 📊 **Analytics** — Learning performance dashboard
- 🏆 **Leaderboard** — Gamified learning
- 🌙 **Dark Mode** — Full theme support
- 📧 **Email OTP** — Secure account verification
