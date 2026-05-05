"""
GENAI EDUCANTION ENGINE — Central AI Client
All AI calls go through this module. 
Using Groq API for high-performance streaming.
"""
import os, json, re
from groq import Groq

# ── API Key ────────────────────────────────────────────────────────────────────
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
client = None

if GROQ_API_KEY:
    client = Groq(api_key=GROQ_API_KEY)
else:
    print("! WARNING: GROQ_API_KEY not found. AI features will be disabled.")

DEFAULT_MODEL = "llama-3.3-70b-versatile"

# ── Mock Data Fallbacks ────────────────────────────────────────────────────────
MOCK_DATA = {
    "quiz": [
        {"text": "What is the primary function of DNA?", "option_a": "Energy storage", "option_b": "Genetic information storage", "option_c": "Protein catalysis", "option_d": "Cell wall structure", "correct_option": "b", "explanation": "DNA (Deoxyribonucleic acid) is the molecule that carries genetic instructions for life."},
        {"text": "Which planet is known as the Red Planet?", "option_a": "Venus", "option_b": "Mars", "option_c": "Jupiter", "option_d": "Saturn", "correct_option": "b", "explanation": "Mars appears red due to iron oxide (rust) on its surface."},
        {"text": "What is the speed of light in a vacuum?", "option_a": "300,000 km/s", "option_b": "150,000 km/s", "option_c": "1,000,000 km/s", "option_d": "500,000 km/s", "correct_option": "a", "explanation": "Light travels at approximately 299,792,458 meters per second."},
        {"text": "What is the chemical symbol for Gold?", "option_a": "Gd", "option_b": "Au", "option_c": "Ag", "option_d": "Fe", "correct_option": "b", "explanation": "Au comes from the Latin word 'Aurum'."},
        {"text": "Who developed the theory of General Relativity?", "option_a": "Isaac Newton", "option_b": "Albert Einstein", "option_c": "Nikola Tesla", "option_d": "Marie Curie", "correct_option": "b", "explanation": "Einstein published General Relativity in 1915."}
    ],
    "flashcards": [
        {"question": "What is Photosynthesis?", "answer": "The process by which green plants and some other organisms use sunlight to synthesize foods with the help of chlorophyll.", "category": "Definition", "difficulty": "Medium"},
        {"question": "Define Inertia.", "answer": "A property of matter by which it continues in its existing state of rest or uniform motion in a straight line, unless changed by an external force.", "category": "Principle", "difficulty": "Hard"},
        {"question": "What is the capital of France?", "answer": "Paris.", "category": "Memory", "difficulty": "Easy"}
    ]
}

# ── Generic chat helper ────────────────────────────────────────────────────────
def chat(messages: list[dict], temperature: float = 0.7, max_tokens: int = 1500) -> str:
    """Send messages to Groq and return the text response."""
    formatted_messages = []
    for m in messages:
        role = "assistant" if m['role'] == 'ai' else m['role']
        formatted_messages.append({"role": role, "content": m['content']})
    
    try:
        if not client:
            return "AI features are currently unavailable (missing API key)."
        completion = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=formatted_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"! Groq AI Error: {e}")
        if "rate limit" in str(e).lower() or "capacity" in str(e).lower():
            return "I'm currently in high-demand mode. How can I help you today?"
        return "I encountered a technical issue. Please try again later."


# ── JSON extractor helper ──────────────────────────────────────────────────────
def extract_json(text: str):
    """Pull the first JSON object or array out of an AI response."""
    try:
        return json.loads(text)
    except Exception:
        pass
    clean = re.sub(r"```(?:json)?", "", text).replace("```", "").strip()
    try:
        return json.loads(clean)
    except Exception:
        pass
    match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", clean)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
    raise ValueError(f"Could not parse JSON from AI response: {text[:300]}")


# ════════════════════════════════════════════════════════════════
#  1. FLASHCARD GENERATION
# ════════════════════════════════════════════════════════════════
def generate_flashcards_ai(topic: str, count: int = 10) -> list[dict]:
    """Generate real educational flashcards using Groq."""
    prompt = f"""You are an expert educator. Generate exactly {count} high-quality flashcards about "{topic}".

Return a JSON array only — no other text. Each object must have:
- "id": integer starting at 1
- "category": one of ["Definition", "Principle", "Application", "Memory", "Quiz"]
- "question": a clear, specific question about {topic}
- "answer": a thorough, accurate explanation (2-4 sentences)
- "difficulty": one of ["Easy", "Medium", "Hard"]

Mix question styles: definitions, how/why questions, true-or-false, fill-in-the-blank, real-world applications.
Make the content genuinely educational and factually accurate.

Return JSON array only, no markdown."""

    text = chat([{"role": "user", "content": prompt}], temperature=0.6, max_tokens=3000)
    cards = extract_json(text)
    for i, c in enumerate(cards):
        c["id"] = i + 1
    return cards[:count]

def generate_flashcards_ai_stream(topic: str, count: int = 10):
    prompt = f"""You are an expert tutor creating study flashcards for "{topic}".

Generate exactly {count} highly effective flashcards.
Return a JSON array only — no other text. Each object must have:
- "id": integer starting at 1
- "category": one of ["Definition", "Principle", "Application", "Memory", "Quiz"]
- "question": a clear, specific question about {topic}
- "answer": a thorough, accurate explanation (2-4 sentences)
- "difficulty": one of ["Easy", "Medium", "Hard"]

Mix question styles: definitions, how/why questions, true-or-false, fill-in-the-blank, real-world applications.
Make the content genuinely educational and factually accurate.

Return JSON array only, no markdown."""
    
    try:
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            stream=True
        )
        for chunk in response:
            content = chunk.choices[0].delta.content
            if content:
                yield content
    except Exception as e:
        print(f"Flashcard Stream Error: {e}")
        yield json.dumps(MOCK_DATA["flashcards"])


# ════════════════════════════════════════════════════════════════
#  2. QUIZ QUESTION GENERATION
# ════════════════════════════════════════════════════════════════
def generate_quiz_ai(topic: str, difficulty: str = "Medium", count: int = 5) -> list[dict]:
    """Generate multiple-choice quiz questions with correct answers and explanations."""
    prompt = f"""You are an expert educator creating a {difficulty}-difficulty quiz on "{topic}".

Generate exactly {count} multiple-choice questions. Return a JSON array only.
Each object must have:
- "text": the question (clear and specific)
- "option_a": first option
- "option_b": second option
- "option_c": third option
- "option_d": fourth option
- "correct_option": one of "a", "b", "c", "d"
- "explanation": why the correct answer is right (2-3 sentences, mention the concept)

Rules:
- All questions must be factually accurate about {topic}
- Wrong options must be plausible (not obviously wrong)
- Vary question types: conceptual, applied, definitional, analytical
- Difficulty should be {difficulty}

Return JSON array only, no markdown, no extra text."""

    text = chat([{"role": "user", "content": prompt}], temperature=0.5, max_tokens=2500)
    return extract_json(text)

def generate_quiz_ai_stream(topic: str, difficulty: str = "Medium", count: int = 5):
    prompt = f"""You are an expert educator creating a {difficulty}-difficulty quiz on "{topic}".

Generate exactly {count} multiple-choice questions. Return a JSON array only.
Each object must have:
- "text": the question (clear and specific)
- "option_a": first option
- "option_b": second option
- "option_c": third option
- "option_d": fourth option
- "correct_option": one of "a", "b", "c", "d"
- "explanation": why the correct answer is right (2-3 sentences, mention the concept)

Rules:
- All questions must be factually accurate about {topic}
- Wrong options must be plausible (not obviously wrong)
- Vary question types: conceptual, applied, definitional, analytical
- Difficulty should be {difficulty}

Return JSON array only, no markdown, no extra text."""
    
    try:
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            stream=True
        )
        for chunk in response:
            content = chunk.choices[0].delta.content
            if content:
                yield content
    except Exception as e:
        print(f"Quiz Stream Error: {e}")
        yield json.dumps(MOCK_DATA["quiz"])


# ════════════════════════════════════════════════════════════════
#  3. CONTENT GENERATION (Notes / Summary / Examples / Case Study)
# ════════════════════════════════════════════════════════════════
CONTENT_PROMPTS = {
    "notes": """You are an expert academic writer. Write comprehensive study notes about "{topic}".

Structure them as follows (use markdown formatting):
## 📑 Study Notes: {topic}

### 1. Core Definition & Overview
[Clear, precise definition + 2-3 sentence overview]

### 2. Key Concepts & Principles
[5-7 bullet points covering the most important ideas, each with a brief explanation]

### 3. Important Facts & Formulas
[Relevant formulas, laws, or key data points with brief context]

### 4. Common Misconceptions
[2-3 things students often get wrong and the correct understanding]

### 5. Real-World Applications
[3 concrete examples of how {topic} is used in practice]

### 6. Study Tips & Memory Aids
[Mnemonics, analogies, or frameworks to remember key ideas]

### 7. Quick Revision Checklist
[5 yes/no questions to self-assess understanding]

Make content factually accurate, specific to {topic}, and educational. Use specific technical details, not generic filler.""",

    "summary": """You are an expert educator. Write a concise but comprehensive summary of "{topic}".

Use this structure (markdown formatting):
## \u26a1 Summary: {topic}

### One-Paragraph Overview
[100-word precise summary capturing what {topic} is and why it matters]

### The 5 Core Points
[5 numbered points, each with a header and 2-sentence explanation]

### Key Terms Defined
[5-7 important vocabulary words with precise definitions]

### How It Connects to Other Fields
[3-4 bullet points showing interdisciplinary connections]

### What You Must Remember
[3 critical takeaways framed as memorable principles]

### Common Exam Questions
[3 typical exam questions about {topic} with brief answer hints]

Be specific, accurate, and educational. Avoid generic filler.""",

    "examples": """You are a master educator. Create detailed worked examples for "{topic}".

Use this structure:
## 💡 Worked Examples: {topic}

### Example 1 — Foundational (Easy)
**Problem:** [Specific, realistic problem about {topic}]
**Step-by-Step Solution:**
[4-5 numbered steps showing the reasoning process]
**Key Insight:** [What this example teaches]

### Example 2 — Intermediate
**Problem:** [More complex, multi-step problem]
**Step-by-Step Solution:**
[5-6 numbered steps with explanations]
**Key Insight:** [The deeper principle illustrated]

### Example 3 — Advanced / Real-World
**Problem:** [Realistic professional or research scenario]
**Approach:**
[Detailed analysis and solution]
**Why This Matters:** [Connection to real applications]

### Common Mistakes to Avoid
[3 specific mistakes students make with {topic} + corrections]

### Practice Problems
[3 unsolved problems of increasing difficulty for self-study]

Use specific, accurate content — not generic templates.""",

    "case_study": """You are an expert academic researcher. Write a detailed case study about "{topic}".

Structure:
## 📊 Case Study: {topic} in Practice

### Background & Context
[Historical or scientific context for {topic}, key milestones]

### Case Study 1: [Specific real-sounding scenario title]
**Situation:** [Detailed description of the challenge]
**Application of {topic}:** [How {topic} principles were applied]
**Outcome & Results:** [Specific, quantified outcomes where possible]
**Lessons Learned:** [3 key takeaways]

### Case Study 2: [Different domain or angle]
**Situation:** [Different context from Case Study 1]
**Application of {topic}:** [Different principles or methods used]
**Outcome & Results:** [Measurable results]
**Lessons Learned:** [3 key takeaways]

### Analysis: What Both Cases Reveal
[Synthesis of patterns and deeper insights about {topic}]

### Critical Discussion Questions
[5 thought-provoking questions for deeper analysis]

### References & Further Reading
[3-4 recommended topics/areas for deeper study]

Make this factually accurate and intellectually rigorous.""",

    "deep_research": """You are an elite academic researcher. Perform a deep, comprehensive research analysis on "{topic}".

Your analysis must be highly detailed and structured for university-level understanding.
Use this structure:
## 🔬 Deep Research Report: {topic}

### 1. Executive Abstract
[A high-level academic summary of what {topic} is, its origin, and its current relevance.]

### 2. Historical Evolution
[Trace the history and timeline of {topic}. Mention key figures, paradigm shifts, and foundational literature.]

### 3. Core Theoretical Frameworks
[Deep dive into the 3-4 primary theories, models, or equations that underpin {topic}. Provide rigorous explanations of how they work.]

### 4. Contemporary Debates & Controversies
[What are the current disagreements in the field regarding {topic}? Detail opposing viewpoints and recent paradigm shifts.]

### 5. Advanced Applications & Edge Cases
[How is {topic} used at the cutting edge of industry or academia? Mention complex, edge-case scenarios where basic models break down.]

### 6. Future Trajectories
[Where is research on {topic} heading in the next 5-10 years? Identify open questions and potential breakthroughs.]

### 7. Core Academic Vocabulary
[Define 8-10 advanced, highly-specific terms related to {topic}.]

Ensure the tone is objective, scholarly, and extremely thorough. Do not use basic introductory language."""
}

def generate_content_ai(topic: str, content_type: str) -> str:
    """Generate educational content using Groq."""
    prompt_template = CONTENT_PROMPTS.get(content_type, CONTENT_PROMPTS["notes"])
    prompt = prompt_template.replace("{topic}", topic)
    return chat([{"role": "user", "content": prompt}], temperature=0.65, max_tokens=2000)

def generate_content_ai_stream(topic: str, content_type: str):
    """Generate educational content using Groq as a stream."""
    prompt_template = CONTENT_PROMPTS.get(content_type, CONTENT_PROMPTS["notes"])
    prompt = prompt_template.replace("{topic}", topic)
    
    try:
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.65,
            stream=True
        )
        for chunk in response:
            content = chunk.choices[0].delta.content
            if content:
                yield content
    except Exception as e:
        print(f"Content Stream Error: {e}")
        yield f"## 📚 Offline Study Guide: {topic}\n\nI'm currently operating in offline mode due to high demand. Here is a brief overview of {topic}:\n\n- **Core Concept**: {topic} is a fundamental area of study involving key principles of theory and practice.\n- **Key Takeaway**: Continuous learning and practice are essential for mastering {topic}.\n\nPlease try again later for a full AI-generated guide!"


# ════════════════════════════════════════════════════════════════
#  4. AI TUTOR CHAT
# ════════════════════════════════════════════════════════════════
TUTOR_SYSTEM = """You are GENAI EDUCANTION ENGINE Tutor — an expert, encouraging academic tutor.

Your personality:
- Knowledgeable across all academic subjects (math, science, programming, history, etc.)
- Patient and encouraging — celebrate progress, never condescending
- Uses clear step-by-step explanations with examples
- Connects concepts to real-world applications
- Asks follow-up questions to check understanding
- Uses markdown formatting (bold key terms, numbered steps, bullet points)
- Keeps responses focused (150-300 words unless asked for more)
- Signs off with a question to keep the student engaged

Never make up facts. If uncertain, say so and suggest how to verify."""

def get_tutor_response(user_message: str, history: list[dict] = None) -> str:
    """Get a real Groq response for the AI tutor."""
    messages = [{"role": "system", "content": TUTOR_SYSTEM}]
    if history:
        for h in history[-6:]:
            role = "assistant" if h["role"] == "ai" else "user"
            messages.append({"role": role, "content": h["content"]})
    messages.append({"role": "user", "content": user_message})
    
    try:
        completion = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=1500,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"Tutor Chat Error: {e}")
        return "I encountered a technical issue. Please try again later."

def get_tutor_response_stream(user_message: str, history: list[dict] = None):
    """Get a streaming real Groq response for the AI tutor."""
    messages = [{"role": "system", "content": TUTOR_SYSTEM}]
    if history:
        for h in history[-6:]:
            role = "assistant" if h["role"] == "ai" else "user"
            messages.append({"role": role, "content": h["content"]})
    messages.append({"role": "user", "content": user_message})
    
    try:
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=messages,
            temperature=0.7,
            stream=True
        )
        for chunk in response:
            content = chunk.choices[0].delta.content
            if content:
                yield content
    except Exception as e:
        print(f"Tutor Stream Error: {e}")
        yield "Hello! I'm currently experiencing some network issues. While my full AI capabilities are temporarily limited, I can still help you with general study tips and basic concept overviews. What are you working on?"


# ════════════════════════════════════════════════════════════════
#  5. UPLOAD / DOCUMENT ANALYSIS
# ════════════════════════════════════════════════════════════════
def analyse_document_ai(text: str, filename: str) -> str:
    """Use Groq to create a structured study summary from uploaded content."""
    truncated = text[:15000] # Groq Llama 3 models support 8k-32k context
    prompt = f"""You are an expert academic tutor. A student has uploaded a document called "{filename}".
Analyse the content and create a comprehensive study summary in markdown.

Document content:
---
{truncated}
---

Create a structured study guide with:
## 📄 Document Analysis: {filename}

### 🎯 Topic & Subject Area
[Identify the main topic and academic subject]

### 📋 Key Concepts Covered
[5-8 bullet points of the main ideas]

### 📍 Critical Facts & Data Points
[Important numbers, formulas, definitions, or facts mentioned]

### 🔍 Detailed Summary
[3-4 paragraph summary of the content]

### 💡 Key Takeaways
[5 numbered learning points]

### \u2753 Study Questions
[5 questions a student should be able to answer after reading this]

### 📚 Suggested Next Steps
[3 recommendations for deeper learning]

Be thorough and educational. Extract real information from the document."""

    try:
        completion = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=2500,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"Document Analysis Error: {e}")
        return f"Failed to analyze document '{filename}'. The file might be too large or there is a temporary network issue."
