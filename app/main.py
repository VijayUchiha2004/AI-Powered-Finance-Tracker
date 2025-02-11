from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict
from datetime import datetime
from app.database import SessionLocal, engine
from models.transaction import Base, Transaction
from services.transaction_service import TransactionService
from services.ai_service import AIService
from app.utils import (
    format_currency,
    calculate_monthly_summary,
    calculate_category_percentages,
    validate_transaction_amount,
    get_date_range_filter,
    generate_transaction_summary
)
from pydantic import BaseModel, Field
from typing import Optional

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI-Powered Finance Tracker")

# Initialize AI Service
ai_service = AIService()

class TransactionCreate(BaseModel):
    amount: float = Field(..., gt=0, description="Transaction amount must be greater than 0")
    description: str = Field(..., min_length=1, description="Transaction description")

class TransactionResponse(BaseModel):
    id: int
    amount: float
    description: str
    predicted_category: str
    confidence_score: float
    date: datetime

    class Config:
        orm_mode = True

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Original endpoints with enhanced validation
@app.post("/transactions/", response_model=TransactionResponse)
def create_transaction(
    transaction: TransactionCreate,
    db: Session = Depends(get_db)
):
    # Validate amount
    error_message = validate_transaction_amount(transaction.amount)
    if error_message:
        raise HTTPException(status_code=400, detail=error_message)
    
    service = TransactionService(db)
    new_transaction = service.create_transaction(
        amount=transaction.amount,
        description=transaction.description
    )
    
    return new_transaction

@app.get("/transactions/", response_model=List[TransactionResponse])
def get_transactions(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    service = TransactionService(db)
    return service.get_transactions(skip=skip, limit=limit)

@app.get("/analysis/")
def get_spending_analysis(db: Session = Depends(get_db)):
    service = TransactionService(db)
    transactions = service.get_transactions()
    
    # Get category totals
    category_totals = service.get_spending_analysis()
    
    # Calculate percentages
    category_percentages = calculate_category_percentages(category_totals)
    
    # Get monthly summary
    monthly_summary = calculate_monthly_summary([
        {
            "amount": t.amount,
            "date": t.date,
            "category": t.predicted_category
        } for t in transactions
    ])

    return {
        "category_totals": {k: format_currency(v) for k, v in category_totals.items()},
        "category_percentages": {k: f"{v:.1f}%" for k, v in category_percentages.items()},
        "monthly_summary": {k: format_currency(v) for k, v in monthly_summary.items()}
    }

# New AI-powered endpoints
@app.get("/insights/")
def get_ai_insights(db: Session = Depends(get_db)):
    """Get AI-powered insights about spending patterns"""
    service = TransactionService(db)
    transactions = service.get_transactions()
    
    # Convert SQLAlchemy objects to dictionaries
    transaction_dicts = [
        {
            "amount": t.amount,
            "predicted_category": t.predicted_category,
            "description": t.description,
            "date": t.date
        } for t in transactions
    ]
    
    insights = ai_service.get_spending_insights(transaction_dicts)
    return {"insights": insights}

@app.get("/anomalies/")
def detect_anomalies(db: Session = Depends(get_db)):
    """Detect unusual spending patterns"""
    service = TransactionService(db)
    transactions = service.get_transactions()
    
    transaction_dicts = [
        {
            "amount": t.amount,
            "predicted_category": t.predicted_category,
            "description": t.description,
            "date": t.date
        } for t in transactions
    ]
    
    anomalies = ai_service.detect_anomalies(transaction_dicts)
    return {"anomalies": anomalies}

@app.post("/budget-suggestion/")
def suggest_budget(income: float, db: Session = Depends(get_db)):
    """Get AI-powered budget suggestions"""
    if income <= 0:
        raise HTTPException(status_code=400, detail="Income must be greater than 0")
    
    service = TransactionService(db)
    transactions = service.get_transactions()
    
    transaction_dicts = [
        {
            "amount": t.amount,
            "predicted_category": t.predicted_category,
            "description": t.description,
            "date": t.date
        } for t in transactions
    ]
    
    budget = ai_service.suggest_budget(transaction_dicts, income)
    return {
        "suggested_budget": {
            category: format_currency(amount)
            for category, amount in budget.items()
        }
    }

@app.get("/future-expenses/")
def predict_expenses(months_ahead: int = 1, db: Session = Depends(get_db)):
    """Predict future expenses"""
    if months_ahead < 1 or months_ahead > 12:
        raise HTTPException(
            status_code=400,
            detail="Months ahead must be between 1 and 12"
        )
    
    service = TransactionService(db)
    transactions = service.get_transactions()
    
    transaction_dicts = [
        {
            "amount": t.amount,
            "predicted_category": t.predicted_category,
            "description": t.description,
            "date": t.date
        } for t in transactions
    ]
    
    predictions = ai_service.predict_future_expenses(transaction_dicts, months_ahead)
    return {
        "predicted_expenses": {
            category: format_currency(amount)
            for category, amount in predictions.items()
        }
    }