from flask import Blueprint, request, jsonify, session, Response, stream_with_context
import json
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

flashcards_bp = Blueprint("flashcards", __name__)

@flashcards_bp.route("/api/flashcards/generate", methods=["POST"])
def generate():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    data  = request.get_json() or {}
    topic = data.get("topic", "").strip()
    count = min(int(data.get("count", 10)), 20)
    if not topic:
        return jsonify({"error": "Topic required"}), 400

    try:
        from ai_client import generate_flashcards_ai
        cards = generate_flashcards_ai(topic, count)
        return jsonify({"cards": cards, "topic": topic, "total": len(cards), "ai_generated": True})
    except Exception as e:
        # Graceful fallback to templates if AI fails
        import random
        CARD_TEMPLATES = {
            "definition": [
                {"q": "What is the core definition of {topic}?", "a": "{topic} is a foundational concept that describes systematic relationships between cause, process, and effect within its domain. It forms the basis for understanding more complex ideas in this field."},
                {"q": "How would you explain {topic} to a beginner?", "a": "Think of {topic} as a structured set of rules and relationships. At its simplest, it governs how inputs transform into outputs through a defined process."},
            ],
            "principle": [
                {"q": "What is the most important principle behind {topic}?", "a": "The key principle of {topic} is that structured, systematic application yields more consistent results. Every element has a defined role."},
                {"q": "What does {topic} help us understand?", "a": "{topic} helps us understand the underlying mechanics of complex systems by breaking them into manageable components and analyzing each relationship independently."},
            ],
            "application": [
                {"q": "Give a real-world example of {topic} in use.", "a": "In practice, {topic} is applied whenever professionals need to solve structured problems systematically — from scientific research to engineering design to business strategy."},
                {"q": "Where would you encounter {topic} in everyday life?", "a": "{topic} appears in many everyday situations: when engineers design systems, when scientists run experiments, and when decision-makers analyze data to choose optimal solutions."},
            ],
            "memory": [
                {"q": "What mnemonic can help remember {topic}?", "a": "Use C-P-A: Concept (what it is), Principle (how it works), Application (where it's used). This covers the three pillars of mastering {topic}."},
                {"q": "What analogy best describes {topic}?", "a": "{topic} is like building a house: the foundation is the core theory, the walls are the supporting principles, and the roof is the advanced applications."},
            ],
            "quiz": [
                {"q": "True or False: {topic} only applies in academic settings.", "a": "FALSE. {topic} has extensive real-world applications across industries including technology, healthcare, business, and scientific research."},
                {"q": "Which best describes {topic}? (A) A random process (B) A structured framework (C) A historical event", "a": "Answer: (B) A structured framework. {topic} provides a systematic approach to understanding and solving problems within its domain."},
            ]
        }
        topic_title = topic.strip().title()
        cards = []
        categories = list(CARD_TEMPLATES.keys())
        for i in range(count):
            cat = categories[i % len(categories)]
            template = random.choice(CARD_TEMPLATES[cat])
            cards.append({
                "id": i + 1,
                "category": cat.title(),
                "question": template["q"].format(topic=topic_title),
                "answer": template["a"].format(topic=topic_title),
                "difficulty": ["Easy", "Medium", "Hard"][i % 3]
            })
        return jsonify({"cards": cards, "topic": topic, "total": len(cards), "ai_generated": False, "fallback_reason": str(e)})

@flashcards_bp.route("/api/flashcards/generate_stream", methods=["POST"])
def generate_stream():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    data  = request.get_json() or {}
    topic = data.get("topic", "").strip()
    count = int(data.get("count", 10))

    if not topic:
        return jsonify({"error": "Topic is required"}), 400

    def generate():
        try:
            from ai_client import generate_flashcards_ai_stream
            for token in generate_flashcards_ai_stream(topic, count):
                yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception as e:
            fallback = f'{{"error": "Generation failed: {str(e)[:60]}"}}'
            yield f"data: {json.dumps({'token': fallback})}\n\n"
        
        yield "data: [DONE]\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')
