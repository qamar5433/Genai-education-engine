import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backend.ai_client import chat

topic = "Cloud Computing"

prompt = f"""You are an expert at creating Mermaid.js mind maps for educational visualization.
Your task is to create a valid Mermaid mind map for the topic: "{topic[:500]}"

Rules for generation:
1. Output ONLY raw Mermaid syntax. No explanations, no markdown blocks (no ```mermaid).
2. The diagram MUST start with the word "mindmap".
3. Use proper indentation for the hierarchy (root, branches, leaves).
4. Keep the text concise and use emojis if they fit the topic.
5. Example structure:
mindmap
  root((Topic))
    Branch 1
      Subtopic A
      Subtopic B
    Branch 2
      Subtopic C

Return the Mermaid code only."""

mermaid_code = chat([{"role": "user", "content": prompt}], temperature=0.3, max_tokens=1000)
with open("output.txt", "w", encoding="utf-8") as f:
    f.write(mermaid_code)
