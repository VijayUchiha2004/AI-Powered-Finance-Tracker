import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///finance_tracker.db')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    MODEL_NAME = "gpt-3.5-turbo"