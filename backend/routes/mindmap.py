from flask import Blueprint, request, jsonify, session
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ai_client import chat

mindmap_bp = Blueprint("mindmap", __name__, url_prefix="/api/mindmap")

@mindmap_bp.route("/generate", methods=["POST"])
def generate_mindmap():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
        
    data = request.get_json() or {}
    topic = data.get("topic", "").strip()
    
    if not topic:
        return jsonify({"error": "Topic is required"}), 400

    prompt = f"""You are an expert at creating hierarchical educational mind maps.
Your task is to create a comprehensive mind map for the topic: "{topic[:500]}"

CRITICAL RULES:
1. Output ONLY a valid JSON object. No markdown, no explanations, no HTML.
2. The JSON must have the following structure:
{{
  "name": "Topic Name (include an emoji)",
  "description": "Short, clear definition or overview of the main topic",
  "children": [
    {{
      "name": "Branch 1 Name (with emoji)",
      "description": "Brief explanation of this branch",
      "children": [
        {{ "name": "Subtopic A", "description": "Definition of Subtopic A" }},
        {{ "name": "Subtopic B", "description": "Definition of Subtopic B" }}
      ]
    }}
  ]
}}
3. Ensure the descriptions are concise (10-15 words max).
4. Ensure the JSON is perfectly formatted.
5. Do not wrap the JSON in ```json blocks. Just raw JSON.

Return the JSON only."""

    try:
        import json
        response_text = chat([{"role": "user", "content": prompt}], temperature=0.3, max_tokens=2000)
        
        # Clean up any accidental markdown blocks
        json_str = response_text.replace("```json", "").replace("```", "").strip()
        
        # Parse and return JSON
        mindmap_data = json.loads(json_str)
        return jsonify({"mindmap_data": mindmap_data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
