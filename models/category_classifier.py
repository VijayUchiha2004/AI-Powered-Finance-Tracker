import openai
from app.config import Config

class CategoryClassifier:
    def __init__(self):
        openai.api_key = Config.OPENAI_API_KEY
        
    def predict_category(self, description: str) -> tuple:
        try:
            response = openai.ChatCompletion.create(
                model=Config.MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are a financial transaction classifier. Categorize the following transaction into one of these categories: 'Food', 'Transportation', 'Shopping', 'Entertainment', 'Bills', 'Other'. Return only the category name and confidence score (0-1) separated by a comma."},
                    {"role": "user", "content": description}
                ]
            )
            
            result = response.choices[0].message.content.strip().split(',')
            category = result[0].strip()
            confidence = float(result[1].strip())
            return category, confidence
        except Exception as e:
            return "Other", 0.0