from sqlalchemy.orm import Session
from models.transaction import Transaction
from models.category_classifier import CategoryClassifier

class TransactionService:
    def __init__(self, db: Session):
        self.db = db
        self.classifier = CategoryClassifier()
    
    def create_transaction(self, amount: float, description: str) -> Transaction:
        predicted_category, confidence = self.classifier.predict_category(description)
        
        transaction = Transaction(
            amount=amount,
            description=description,
            predicted_category=predicted_category,
            confidence_score=confidence
        )
        
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        return transaction
    
    def get_transactions(self, skip: int = 0, limit: int = 100):
        return self.db.query(Transaction).offset(skip).limit(limit).all()
    
    def get_spending_analysis(self):
        transactions = self.db.query(Transaction).all()
        categories = {}
        
        for transaction in transactions:
            category = transaction.predicted_category
            if category in categories:
                categories[category] += transaction.amount
            else:
                categories[category] = transaction.amount
                
        return categories