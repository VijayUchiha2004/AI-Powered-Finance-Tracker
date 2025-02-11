import openai
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from app.config import Config
from statistics import mean, stdev

class AIService:
    def __init__(self):
        openai.api_key = Config.OPENAI_API_KEY
        self.model_name = Config.MODEL_NAME

    def get_spending_insights(self, transactions: List[Dict]) -> str:
        """
        Generate AI-powered insights about spending patterns
        """
        if not transactions:
            return "No transactions available for analysis."

        # Prepare transaction data for GPT
        transaction_text = "\n".join([
            f"Amount: ${t['amount']}, Category: {t['predicted_category']}, " 
            f"Description: {t['description']}"
            for t in transactions[-10:]  # Last 10 transactions
        ])

        try:
            response = openai.ChatCompletion.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a financial advisor. Analyze these transactions and provide useful insights about spending patterns and suggestions for improvement. Be concise and specific."},
                    {"role": "user", "content": f"Here are the recent transactions:\n{transaction_text}"}
                ]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Unable to generate insights at this time: {str(e)}"

    def detect_anomalies(self, transactions: List[Dict]) -> List[Dict]:
        """
        Detect unusual spending patterns or potential fraudulent transactions
        """
        if len(transactions) < 2:
            return []

        anomalies = []
        category_averages = {}
        category_stddev = {}

        # Calculate average and standard deviation for each category
        for transaction in transactions:
            category = transaction['predicted_category']
            amount = transaction['amount']
            
            if category not in category_averages:
                category_averages[category] = []
            category_averages[category].append(amount)

        for category, amounts in category_averages.items():
            if len(amounts) >= 2:
                category_averages[category] = mean(amounts)
                category_stddev[category] = stdev(amounts)
            else:
                category_averages[category] = amounts[0]
                category_stddev[category] = 0

        # Detect anomalies (transactions > 2 standard deviations from mean)
        for transaction in transactions:
            category = transaction['predicted_category']
            amount = transaction['amount']
            
            if category_stddev[category] > 0:
                z_score = abs(amount - category_averages[category]) / category_stddev[category]
                if z_score > 2:
                    anomalies.append({
                        'transaction': transaction,
                        'reason': f"Amount is unusually {'high' if amount > category_averages[category] else 'low'} for this category",
                        'severity': 'high' if z_score > 3 else 'medium'
                    })

        return anomalies

    def suggest_budget(self, transactions: List[Dict], income: float) -> Dict[str, float]:
        """
        Generate AI-powered budget suggestions based on spending history and income
        """
        # Calculate current spending by category
        category_spending = {}
        for transaction in transactions:
            category = transaction['predicted_category']
            amount = transaction['amount']
            if category in category_spending:
                category_spending[category] += amount
            else:
                category_spending[category] = amount

        try:
            # Convert spending data to text for GPT
            spending_text = "\n".join([
                f"{category}: ${amount:.2f}" 
                for category, amount in category_spending.items()
            ])

            response = openai.ChatCompletion.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a financial advisor. Based on the current spending patterns and income, suggest a monthly budget allocation. Return only category:amount pairs, comma-separated."},
                    {"role": "user", "content": f"Monthly income: ${income}\nCurrent monthly spending:\n{spending_text}"}
                ]
            )

            # Parse GPT response into dictionary
            budget_text = response.choices[0].message.content.strip()
            budget_pairs = [pair.strip() for pair in budget_text.split(',')]
            budget = {}
            
            for pair in budget_pairs:
                category, amount = pair.split(':')
                budget[category.strip()] = float(amount.strip().replace('$', ''))

            return budget
        except Exception as e:
            # Fallback to simple percentage-based budget if AI fails
            return self._generate_simple_budget(income)

    def _generate_simple_budget(self, income: float) -> Dict[str, float]:
        """
        Fallback method to generate a simple budget based on common guidelines
        """
        return {
            'Housing': income * 0.3,
            'Food': income * 0.15,
            'Transportation': income * 0.1,
            'Utilities': income * 0.1,
            'Entertainment': income * 0.05,
            'Shopping': income * 0.1,
            'Savings': income * 0.15,
            'Other': income * 0.05
        }

    def predict_future_expenses(self, transactions: List[Dict], months_ahead: int = 1) -> Dict[str, float]:
        """
        Predict future expenses based on historical spending patterns
        """
        if not transactions:
            return {}

        # Group transactions by category and calculate monthly averages
        category_totals = {}
        for transaction in transactions:
            category = transaction['predicted_category']
            amount = transaction['amount']
            if category in category_totals:
                category_totals[category].append(amount)
            else:
                category_totals[category] = [amount]

        predictions = {}
        for category, amounts in category_totals.items():
            avg_monthly = mean(amounts)
            # Add simple trend analysis
            if len(amounts) >= 2:
                trend = (amounts[-1] - amounts[0]) / len(amounts)
                predicted_amount = avg_monthly + (trend * months_ahead)
            else:
                predicted_amount = avg_monthly

            predictions[category] = max(0, predicted_amount)  # Ensure no negative predictions

        return predictions