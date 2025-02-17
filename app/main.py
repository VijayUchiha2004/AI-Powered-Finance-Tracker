from fastapi import FastAPI, Depends, HTTPException, Request, Form
from sqlalchemy.orm import Session
from typing import List, Dict
from datetime import datetime, timedelta
from app.database import SessionLocal, engine
from models.transaction import Base, Transaction
from services.transaction_service import TransactionService
from services.ai_service import AIService
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
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
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware
import os
import logging
from dotenv import load_dotenv
import random  # For demo data, replace with real data later
from .models.database import get_db, User, Transaction
from passlib.context import CryptContext
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import secrets
import re

load_dotenv()

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI-Powered Finance Tracker")

# Initialize AI Service
ai_service = AIService()

# OAuth setup
oauth = OAuth()
oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_params=None,
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    client_kwargs={'scope': 'openid email profile'}
)

oauth.register(
    name='github',
    client_id=os.getenv('GITHUB_CLIENT_ID'),
    client_secret=os.getenv('GITHUB_CLIENT_SECRET'),
    access_token_url='https://github.com/login/oauth/access_token',
    access_token_params=None,
    authorize_url='https://github.com/login/oauth/authorize',
    authorize_params=None,
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'user:email'}
)

# Session middleware with secure configuration
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv('SECRET_KEY', 'your-secret-key-here'),
    session_cookie="finance_tracker_session",
    max_age=86400,  # 24 hours
    same_site='lax',  # Prevents CSRF
    https_only=False  # Set to True if using HTTPS
)

# Add logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Add this debugging section
print("Environment variables:")
print(f"GITHUB_CLIENT_ID: {'set' if os.getenv('GITHUB_CLIENT_ID') else 'not set'}")
print(f"GITHUB_CLIENT_SECRET: {'set' if os.getenv('GITHUB_CLIENT_SECRET') else 'not set'}")
print(f"SECRET_KEY: {'set' if os.getenv('SECRET_KEY') else 'not set'}")

# Add these at the top with your other imports
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Add these to your existing imports and configurations
EMAIL_VERIFICATION_SECRET = os.getenv("EMAIL_VERIFICATION_SECRET", "your-secret-key")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "your-email@gmail.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "your-app-password")

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

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

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

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Auth routes
@app.get("/")
async def root(request: Request):
    user = request.session.get('user')
    if not user:
        return RedirectResponse(url="/login")
    return FileResponse("app/static/index.html")

@app.get("/login")
async def login_page():
    return FileResponse("app/static/login.html")

@app.get('/auth/google/login')
async def google_login(request: Request):
    redirect_uri = request.url_for('google_auth')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@app.get('/auth/google/callback')
async def google_auth(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user = await oauth.google.parse_id_token(request, token)
    request.session['user'] = dict(user)
    return RedirectResponse(url='/')

@app.get('/auth/github/login')
async def github_login(request: Request):
    try:
        redirect_uri = request.url_for('github_auth')
        print(f"Starting GitHub OAuth flow")
        print(f"Redirect URI: {redirect_uri}")
        return await oauth.github.authorize_redirect(request, redirect_uri)
    except Exception as e:
        print(f"Error in github_login: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "type": type(e).__name__}
        )

@app.get('/auth/github/callback')
async def github_auth(request: Request, db: Session = Depends(get_db)):
    try:
        logger.debug("Starting GitHub callback")
        token = await oauth.github.authorize_access_token(request)
        logger.debug("Got access token")
        
        resp = await oauth.github.get('user', token=token)
        user_data = resp.json()
        logger.debug(f"GitHub user data: {user_data.get('login')}")
        
        # Check if user exists
        user = db.query(User).filter(User.github_id == str(user_data['id'])).first()
        
        if not user:
            logger.debug("Creating new user")
            user = User(
                github_id=str(user_data['id']),
                email=user_data.get('email'),
                name=user_data.get('name') or user_data['login']
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.debug(f"Created user with ID: {user.id}")
        else:
            logger.debug(f"Found existing user with ID: {user.id}")
        
        # Store user data in session
        request.session['user'] = {
            'id': user.id,
            'name': user.name,
            'email': user.email
        }
        logger.debug("User data stored in session")
        
        # Simplified redirect with status code
        return RedirectResponse(
            url='/',
            status_code=303  # Using 303 See Other to ensure GET request
        )
        
    except Exception as e:
        logger.error(f"GitHub callback error: {str(e)}")
        logger.exception(e)
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "type": type(e).__name__}
        )

@app.get('/auth/logout')
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login")

@app.get("/api/user")
async def get_user(request: Request):
    user = request.session.get('user')
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

@app.get("/api/quick-stats")
async def get_quick_stats(request: Request, db: Session = Depends(get_db)):
    user = request.session.get('user')
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    transactions = db.query(Transaction).filter(Transaction.user_id == user['id']).all()
    
    total_spending = sum(t.amount for t in transactions) if transactions else 0
    largest_expense = max((t.amount for t in transactions), default=0)
    transaction_count = len(transactions)
    monthly_average = total_spending / 30 if transactions else 0
    
    return {
        "total_spending": round(total_spending, 2),
        "monthly_average": round(monthly_average, 2),
        "largest_expense": round(largest_expense, 2),
        "transaction_count": transaction_count
    }

@app.get("/api/transactions")
async def get_transactions(request: Request, db: Session = Depends(get_db)):
    user = request.session.get('user')
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    transactions = db.query(Transaction)\
        .filter(Transaction.user_id == user['id'])\
        .order_by(Transaction.date.desc())\
        .all()
    
    return [
        {
            "id": t.id,
            "amount": t.amount,
            "description": t.description,
            "category": t.category,
            "date": t.date.isoformat(),
            "predicted_category": t.predicted_category or "",
            "confidence_score": t.confidence_score or 0.0
        }
        for t in transactions
    ]

@app.get("/api/analysis")
async def get_analysis(request: Request, period: str = 'month', db: Session = Depends(get_db)):
    user = request.session.get('user')
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Calculate date range based on period
    now = datetime.now()
    if period == 'week':
        start_date = now - timedelta(days=7)
    elif period == 'month':
        start_date = now - timedelta(days=30)
    elif period == 'year':
        start_date = now - timedelta(days=365)
    else:
        start_date = now - timedelta(days=30)  # default to month
    
    # Get transactions for the period
    transactions = db.query(Transaction)\
        .filter(Transaction.user_id == user['id'])\
        .filter(Transaction.date >= start_date)\
        .order_by(Transaction.date.asc())\
        .all()
    
    # Initialize data structures
    daily_spending = {}
    category_totals = {}
    
    # Generate all dates in the range for complete data
    date_range = []
    delta = now - start_date
    for i in range(delta.days + 1):
        date = (start_date + timedelta(days=i)).strftime('%Y-%m-%d')
        daily_spending[date] = 0
        date_range.append(date)
    
    # Process transactions
    for t in transactions:
        date_str = t.date.strftime('%Y-%m-%d')
        daily_spending[date_str] = daily_spending.get(date_str, 0) + abs(t.amount)
        
        category = t.category or 'Other'
        category_totals[category] = category_totals.get(category, 0) + abs(t.amount)
    
    return {
        "spending_trends": {
            "dates": date_range,
            "amounts": [daily_spending[date] for date in date_range]
        },
        "category_totals": category_totals
    }

# Add this endpoint for debugging
@app.get("/api/debug/transactions")
async def debug_transactions(request: Request, db: Session = Depends(get_db)):
    """Endpoint to check what transactions exist in the database"""
    user = request.session.get('user')
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    transactions = db.query(Transaction)\
        .filter(Transaction.user_id == user['id'])\
        .order_by(Transaction.date.desc())\
        .all()
    
    return [{
        "id": t.id,
        "amount": t.amount,
        "description": t.description,
        "category": t.category,
        "date": t.date.isoformat()
    } for t in transactions]

@app.post("/api/transactions")
async def create_transaction(
    request: Request,
    transaction: dict,
    db: Session = Depends(get_db)
):
    user = request.session.get('user')
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    new_transaction = Transaction(
        user_id=user['id'],
        amount=transaction['amount'],
        description=transaction['description'],
        category=transaction['category'],
        date=datetime.now()
    )
    
    db.add(new_transaction)
    db.commit()
    db.refresh(new_transaction)
    
    return {"status": "success", "transaction": {
        "amount": new_transaction.amount,
        "description": new_transaction.description,
        "category": new_transaction.category,
        "date": new_transaction.date.isoformat()
    }}

# Add this test endpoint to verify session
@app.get('/test-session')
async def test_session(request: Request):
    return {
        "session": request.session.get('user'),
        "cookies": request.cookies
    }

@app.get("/signup")
async def signup_page():
    return FileResponse("app/static/signup.html")

def validate_password(password: str) -> tuple[bool, str]:
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number"
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character"
    return True, "Password is strong"

def send_verification_email(email: str, token: str):
    """Send verification email to user"""
    msg = MIMEMultipart()
    msg['From'] = SMTP_USERNAME
    msg['To'] = email
    msg['Subject'] = "Verify your AI Finance Tracker account"
    
    verification_link = f"http://localhost:8000/verify-email?token={token}"
    
    body = f"""
    <html>
        <body>
            <h2>Welcome to AI Finance Tracker!</h2>
            <p>Thank you for signing up. Please verify your email address by clicking the link below:</p>
            <p>
                <a href="{verification_link}" style="
                    background-color: #2563eb;
                    color: white;
                    padding: 12px 24px;
                    text-decoration: none;
                    border-radius: 6px;
                    display: inline-block;
                    margin: 16px 0;
                ">Verify Email</a>
            </p>
            <p>If you didn't create an account, you can safely ignore this email.</p>
        </body>
    </html>
    """
    
    msg.attach(MIMEText(body, 'html'))
    
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print(f"Failed to send email: {e}")
        raise HTTPException(status_code=500, detail="Failed to send verification email")

@app.post("/auth/signup")
async def signup(user_data: UserCreate, db: Session = Depends(get_db)):
    try:
        # Check if username or email already exists
        existing_user = db.query(User).filter(
            (User.username == user_data.username) | (User.email == user_data.email)
        ).first()
        
        if existing_user:
            if existing_user.username == user_data.username:
                raise HTTPException(status_code=400, detail="Username already taken")
            else:
                raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create new user
        hashed_password = pwd_context.hash(user_data.password)
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            password=hashed_password,
            is_verified=True  # Setting to True for now to skip email verification
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return JSONResponse(
            status_code=200,
            content={"message": "User created successfully"}
        )
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Signup error: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")

@app.get("/verify-email")
async def verify_email(token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.verification_token == token).first()
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid verification token")
    
    if user.is_verified:
        return FileResponse("app/static/login.html")
    
    user.is_verified = True
    user.verification_token = None
    db.commit()
    
    return FileResponse("app/static/login.html")

@app.post("/auth/login")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    try:
        user = db.query(User).filter(User.username == form_data.username).first()
        
        if not user or not pwd_context.verify(form_data.password, user.password):
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid username or password"}
            )
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        
        # Set session
        request.session['user'] = {
            'id': user.id,
            'username': user.username,
            'email': user.email
        }
        
        return JSONResponse(
            status_code=200,
            content={"message": "Login successful"}
        )
        
    except Exception as e:
        logging.error(f"Login error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Login failed"}
        )

# Add login check endpoint
@app.get("/api/check-auth")
async def check_auth(request: Request):
    user = request.session.get('user')
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"authenticated": True, "user": user}