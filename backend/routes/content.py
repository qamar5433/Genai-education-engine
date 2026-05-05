from flask import Blueprint, request, jsonify, session, Response, stream_with_context
import json
import sys, os
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import SessionLocal
from models import Enrollment, User

content_bp = Blueprint("content", __name__)

@content_bp.route("/api/content/generate", methods=["POST"])
def generate():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    data         = request.get_json() or {}
    topic        = data.get("topic", "").strip()
    content_type = data.get("type", "notes")
    course_id    = data.get("course_id")
    if not topic:
        return jsonify({"error": "Topic is required"}), 400
    
    # Update activity if course_id provided
    if course_id:
        try:
            cid = int(course_id)
            db = SessionLocal()
            try:
                enr = db.query(Enrollment).filter_by(user_id=session["user_id"], course_id=cid).first()
                if enr:
                    enr.last_active = datetime.utcnow()
                    # Real-time progress boost for reading (2% per read, capped)
                    enr.progress_pct = min(100.0, (enr.progress_pct or 0) + 2.0)
                    
                    # Tiny XP bonus for reading
                    user = db.query(User).filter_by(id=session["user_id"]).first()
                    if user: user.xp += 5
                    db.commit()
            finally:
                db.close()
        except (ValueError, TypeError):
            pass

    try:
        from ai_client import generate_content_ai
        result = generate_content_ai(topic, content_type)
        return jsonify({"content": result, "topic": topic, "type": content_type, "ai_generated": True})
    except Exception as e:
        # Fallback to rich templates
        topic_title = topic.strip().title()
        fallbacks = {
            "notes": f"""## 📝 Study Notes: {topic_title}

### 1. Core Definition
{topic_title} is a foundational domain combining theoretical principles with practical methods to solve specific categories of problems across multiple disciplines.

### 2. Key Concepts
- **Core Principle A** — The primary mechanism driving {topic_title} at a fundamental level
- **Core Principle B** — Secondary patterns observed across different applications
- **Core Principle C** — Advanced extensions that build on the base theory
- **Core Principle D** — Integration points with adjacent fields

### 3. Important Rules / Formulas
- Rule 1: Structured input → defined process → measurable output
- Rule 2: Cause-effect relationships are central to understanding outcomes
- Rule 3: Iterative practice accelerates mastery

### 4. Common Misconceptions
- ⚠ Confusing surface patterns with deep structural rules.
- ⚠ Skipping foundational understanding in favour of memorization.

### 5. Real-World Applications
1. Applied in scientific research to design controlled experiments
2. Used in engineering to optimize system performance
3. Central to data-driven decision-making in business contexts

### 6. Quick Recall — C-P-A Framework
**Concept** → **Principle** → **Application**

📌 *Revisit after 24 hours for spaced repetition.*""",

            "summary": f"""## ⚡ Summary: {topic_title}

### One-Paragraph Overview
{topic_title} is a structured domain of knowledge that combines theoretical principles with practical applications. It provides frameworks for systematic problem-solving and informed decision-making across academic and professional contexts.

### The 5 Core Points
1. **Foundation** — Built on well-established principles with broad applicability
2. **Process** — Follows structured methodology: analyse → apply → evaluate
3. **Application** — Real-world impact across multiple fields
4. **Mastery Path** — Requires conceptual clarity + hands-on practice
5. **Connection** — Integrates with adjacent disciplines for richer insight

### Key Terms
- *Core concept*: The foundational unit of understanding in {topic_title}
- *Framework*: The structured approach used to apply {topic_title}
- *Application domain*: The specific contexts where {topic_title} is used

### What You Must Remember
→ Understanding *why* matters more than memorizing *what*
→ Real examples reveal patterns not obvious from theory alone
→ Teaching the concept to others is the highest form of mastery""",

            "examples": f"""## 💡 Worked Examples: {topic_title}

### Example 1 — Foundational
**Scenario:** A student encounters {topic_title} for the first time.
**Approach:**
1. Identify the core definition and scope
2. Find a familiar analogy to anchor understanding
3. Work through simple exercises to build intuition
4. Reflect on what clicked and what needs review
**Key Insight:** Mental models form faster through examples than definitions.

### Example 2 — Intermediate
**Scenario:** Applying {topic_title} to a multi-variable problem.
**Approach:**
1. Break the problem into sub-components
2. Apply the relevant {topic_title} principle to each part
3. Synthesize results into a coherent answer
4. Verify against known constraints
**Key Insight:** Decomposition is the key to complex problem-solving.

### Example 3 — Advanced / Real-World
**Scenario:** A professional uses {topic_title} to make a high-stakes decision.
**Approach:**
1. Frame the decision space using {topic_title} principles
2. Identify highest-leverage variables
3. Apply domain knowledge to filter options
4. Document reasoning for accountability
**Key Insight:** Deep understanding enables confident decision-making under pressure.

### Common Mistakes
❌ Jumping to solutions without understanding the problem
✅ Decompose → Analyse → Apply → Verify → Communicate""",

            "case_study": f"""## 📊 Case Study: {topic_title}

### Case Study 1: Academic Setting
**Challenge:** Students consistently struggled with {topic_title}, showing a 38% failure rate.
**Approach:**
- Implemented active recall sessions focused on {topic_title} fundamentals
- Introduced peer-teaching workshops
- Created visual concept maps
- Added weekly mini-assessments with immediate feedback
**Results:** Failure rate dropped to 11% · Average score improved by 26 points · Confidence increased 60%
**Lesson:** Structured, spaced engagement with {topic_title} outperforms passive review.

### Case Study 2: Industry Application
**Challenge:** Engineers lacked applied knowledge of {topic_title}, leading to costly errors.
**Approach:**
- 4-week intensive bootcamp on {topic_title} principles
- Hands-on projects applying concepts to real challenges
- Senior-junior mentorship pairing
**Results:** Error costs reduced by 33% · Project timelines shortened by 18%
**Lesson:** Applied learning of {topic_title} creates compound value in professional settings.

### Discussion Questions
1. What factors made both interventions successful?
2. How would you adapt these to your own learning of {topic_title}?
3. What metrics would you use to track your own progress?"""
        }
        result = fallbacks.get(content_type, fallbacks["notes"])
        return jsonify({"content": result, "topic": topic_title, "type": content_type, "ai_generated": False})

@content_bp.route("/api/content/generate_stream", methods=["POST"])
def generate_stream():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    data         = request.get_json() or {}
    topic        = data.get("topic", "").strip()
    content_type = data.get("type", "notes")
    if not topic:
        return jsonify({"error": "Topic is required"}), 400
    if len(topic) > 200:
        return jsonify({"error": "Topic too long"}), 400
    if content_type not in ("notes", "summary", "examples", "case_study", "deep_research"):
        return jsonify({"error": "Invalid content type"}), 400

    def generate():
        try:
            from ai_client import generate_content_ai_stream
            for token in generate_content_ai_stream(topic, content_type):
                yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        yield "data: [DONE]\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')
