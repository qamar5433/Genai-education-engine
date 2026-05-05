from flask import Blueprint, request, jsonify, session
import sys, os, re, io
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

upload_bp = Blueprint("upload", __name__)

import PyPDF2
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs

ALLOWED_EXTENSIONS = {".txt", ".md", ".py", ".js", ".html", ".css", ".csv", ".json", ".pdf"}

def extract_text(filename: str, content_bytes: bytes) -> str:
    try:
        return content_bytes.decode("utf-8", errors="replace")
    except Exception:
        return content_bytes.decode("latin-1", errors="replace")

def extract_pdf_text(content_bytes: bytes) -> str:
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(content_bytes))
        text = ""
        for page in reader.pages:
            if page.extract_text():
                text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        print(f"PDF Extraction error: {e}")
        return ""

def get_youtube_transcript(url: str) -> str:
    try:
        query = urlparse(url)
        if query.hostname == 'youtu.be':
            video_id = query.path[1:]
        elif query.hostname in ('www.youtube.com', 'youtube.com'):
            if query.path == '/watch':
                video_id = parse_qs(query.query)['v'][0]
            elif query.path.startswith('/embed/'):
                video_id = query.path.split('/')[2]
            elif query.path.startswith('/v/'):
                video_id = query.path.split('/')[2]
            else:
                return ""
        else:
            return ""
        
        api = YouTubeTranscriptApi()
        transcripts = api.list(video_id)
        # Find English transcript (try a few common language codes)
        try:
            transcript = transcripts.find_transcript(['en', 'en-US', 'en-GB'])
        except Exception:
            # If English not found, grab the first available transcript
            transcript = next(iter(transcripts._manually_created_transcripts.values()), None)
            if not transcript:
                transcript = next(iter(transcripts._generated_transcripts.values()), None)
            if not transcript:
                return ""
                
        transcript_list = transcript.fetch()
        text = " ".join([d['text'] for d in transcript_list])
        return text
    except Exception as e:
        print(f"YouTube Transcript error: {e}")
        return ""

def basic_summarize(text: str, filename: str) -> str:
    """Fallback summary if AI is unavailable."""
    words      = text.split()
    word_count = len(words)
    lines      = [l.strip() for l in text.splitlines() if l.strip()]
    key_lines  = lines[:8]
    sentences  = [s.strip() for s in re.split(r"[.!?]+", text) if len(s.strip()) > 20]
    read_time  = max(1, round(word_count / 200))

    summary_lines = [f"## 📄 Document Summary: {filename}", ""]
    summary_lines.append(f"**Words:** {word_count:,}  ·  **Estimated read time:** {read_time} min")
    summary_lines.append("")
    summary_lines.append("### 🔑 Key Content Preview")
    for i, kp in enumerate(key_lines, 1):
        summary_lines.append(f"{i}. {kp[:150]}")
    summary_lines.append("")
    if sentences:
        summary_lines.append("### 📝 Opening Lines")
        for s in sentences[:5]:
            summary_lines.append(f"- {s[:200]}")
    return "\n".join(summary_lines)

@upload_bp.route("/api/upload/parse", methods=["POST"])
def parse_upload():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    # Handle JSON body (pasted text)
    if request.content_type and "application/json" in request.content_type:
        data = request.get_json(silent=True) or {}
        raw  = data.get("text", "").strip()
        name = data.get("filename", "pasted_text.md")
        youtube_url = data.get("youtube_url", "").strip()
        
        if youtube_url:
            text = get_youtube_transcript(youtube_url)
            if not text:
                return jsonify({"error": "Could not fetch transcript. Ensure the video is public and has closed captions enabled."}), 400
            filename = "YouTube Video Transcript"
        elif raw:
            text = raw
            filename = name
        else:
            return jsonify({"error": "No text or YouTube URL provided"}), 400
    elif "file" in request.files:
        file     = request.files["file"]
        filename = file.filename or "upload.txt"
        ext      = os.path.splitext(filename.lower())[1]
        if ext not in ALLOWED_EXTENSIONS:
            return jsonify({"error": f"Unsupported file type '{ext}'."}), 400
        content_bytes = file.read()
        if len(content_bytes) > 10_000_000:
            return jsonify({"error": "File too large. Max 10 MB."}), 400
        
        if ext == ".pdf":
            text = extract_pdf_text(content_bytes)
            if not text:
                return jsonify({"error": "Failed to extract text from PDF or PDF is empty/scanned."}), 400
        else:
            text = extract_text(filename, content_bytes)
    else:
        return jsonify({"error": "No file or text provided"}), 400

    word_count = len(text.split())
    read_time  = max(1, round(word_count / 200))

    # Try AI analysis
    try:
        from ai_client import analyse_document_ai
        preview = analyse_document_ai(text, filename)
        ai_generated = True
    except Exception as e:
        preview = basic_summarize(text, filename)
        ai_generated = False

    return jsonify({
        "success":      True,
        "filename":     filename,
        "word_count":   word_count,
        "read_time":    read_time,
        "preview":      preview,
        "raw_text":     text[:4000],
        "ai_generated": ai_generated
    })
