import google.generativeai as genai
import os

genai.configure(api_key="AIzaSyDevPCC7MEle1Dsw4YcRccyp4bEc2I9Uow")
model = genai.GenerativeModel('gemini-1.5-flash')

try:
    response = model.generate_content("Say hello in one word")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
