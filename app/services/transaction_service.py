from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from sqlalchemy import func
from typing import List, Dict
from ..models.database import Transaction, User

class TransactionService:
    @staticmethod
    async def create_transaction(db: Session, user_id: int, amount: float, description: str, category: str = None):
        transaction = Transaction(
            user_id=user_id,
            amount=amount,
            description=description,
            category=category
        )
        db.add(transaction)
        db.commit()
        db.refresh(transaction)
        return transaction

    @staticmethod
    async def get_user_transactions(db: Session, user_id: int) -> List[Transaction]:
        return db.query(Transaction).filter(Transaction.user_id == user_id).all()

    @staticmethod
    def get_quick_stats(db: Session, user_id: int) -> Dict:
        transactions = db.query(Transaction)\
            .filter(Transaction.user_id == user_id)\
            .all()
        
        if not transactions:
            return {
                "total_spending": 0,
                "monthly_average": 0,
                "largest_expense": 0,
                "transaction_count": 0
            }

        total_spending = sum(t.amount for t in transactions)
        largest_expense = max(t.amount for t in transactions)
        transaction_count = len(transactions)
        
        # Calculate monthly average
        if transaction_count > 0:
            oldest_transaction = min(t.date for t in transactions)
            months = max(1, (datetime.now() - oldest_transaction).days / 30)
            monthly_average = total_spending / months
        else:
            monthly_average = 0

        return {
            "total_spending": round(total_spending, 2),
            "monthly_average": round(monthly_average, 2),
            "largest_expense": round(largest_expense, 2),
            "transaction_count": transaction_count
        }

    @staticmethod
    def get_spending_analysis(db: Session, user_id: int) -> Dict:
        thirty_days_ago = datetime.now() - timedelta(days=30)
        transactions = db.query(Transaction)\
            .filter(Transaction.user_id == user_id)\
            .filter(Transaction.date >= thirty_days_ago)\
            .all()

        # Initialize with demo data if no transactions
        if not transactions:
            return {
                "spending_trends": {
                    "dates": [(datetime.now() - timedelta(days=x)).strftime('%Y-%m-%d') for x in range(30)],
                    "amounts": [0] * 30
                },
                "category_totals": {
                    "Food": 0,
                    "Transportation": 0,
                    "Entertainment": 0,
                    "Shopping": 0,
                    "Bills": 0
                }
            }

        # Prepare data structures
        daily_spending = {}
        category_totals = {}

        for t in transactions:
            date_str = t.date.strftime('%Y-%m-%d')
            daily_spending[date_str] = daily_spending.get(date_str, 0) + t.amount
            
            category = t.category or 'Uncategorized'
            category_totals[category] = category_totals.get(category, 0) + t.amount

        return {
            "spending_trends": {
                "dates": list(daily_spending.keys()),
                "amounts": list(daily_spending.values())
            },
            "category_totals": category_totals
        } 