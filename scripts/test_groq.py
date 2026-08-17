import os
from dotenv import load_dotenv

load_dotenv()
from groq import Groq

api_key = os.getenv("GROQ_API_KEY")
print(f"API Key: {api_key[:20]}...{api_key[-10:] if api_key else 'NOT SET'}")

client = Groq(api_key=api_key)
response = client.chat.completions.create(
    model="llama-3.1-8b-instant",
    messages=[{"role": "user", "content": "Say OK"}]
)
print("Response:", response.choices[0].message.content)
print("✅ Groq API key is valid and working!")
