import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ai_client import generate_quiz_ai
try:
    print("Testing AI generation...")
    res = generate_quiz_ai("Science", count=1)
    print("SUCCESS:", res)
except Exception as e:
    print("ERROR:", e)
