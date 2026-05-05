import google.generativeai as genai
import os

genai.configure(api_key="AIzaSyDevPCC7MEle1Dsw4YcRccyp4bEc2I9Uow")

for m in genai.list_models():
  if 'generateContent' in m.supported_generation_methods:
    print(m.name)
