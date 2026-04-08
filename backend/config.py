import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_AI_API_KEY = os.getenv("GOOGLE_AI_API_KEY")

if not GOOGLE_AI_API_KEY:
    raise ValueError("GOOGLE_AI_API_KEY not set. Copy .env.example to .env and add your key.")
