from datetime import datetime
from typing import Dict, List, Optional
from decimal import Decimal, ROUND_HALF_UP

def format_currency(amount: float) -> str:
    """
    Format amount to currency string with 2 decimal places
    """
    decimal_amount = Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return f"${decimal_amount:,.2f}"

def calculate_monthly_summary(transactions: List[Dict]) -> Dict:
    """
    Calculate monthly spending summary from transactions
    """
    monthly_totals = {}
    
    for transaction in transactions:
        date = transaction.get('date')
        if isinstance(date, str):
            date = datetime.strptime(date, '%Y-%m-%dT%H:%M:%S.%f')
        
        month_key = date.strftime('%Y-%m')
        amount = transaction.get('amount', 0)
        
        if month_key in monthly_totals:
            monthly_totals[month_key] += amount
        else:
            monthly_totals[month_key] = amount
    
    return monthly_totals

def calculate_category_percentages(category_totals: Dict[str, float]) -> Dict[str, float]:
    """
    Calculate percentage distribution of spending by category
    """
    total_spending = sum(category_totals.values())
    if total_spending == 0:
        return {category: 0.0 for category in category_totals}
    
    return {
        category: (amount / total_spending * 100)
        for category, amount in category_totals.items()
    }

def validate_transaction_amount(amount: float) -> Optional[str]:
    """
    Validate transaction amount
    Returns error message if invalid, None if valid
    """
    if amount <= 0:
        return "Transaction amount must be greater than 0"
    if amount > 1000000:  # $1M limit as an example
        return "Transaction amount exceeds maximum limit"
    return None

def get_date_range_filter(start_date: Optional[datetime] = None, 
                         end_date: Optional[datetime] = None) -> Dict:
    """
    Create date range filter for database queries
    """
    date_filter = {}
    if start_date:
        date_filter['date_gte'] = start_date
    if end_date:
        date_filter['date_lte'] = end_date
    return date_filter

def generate_transaction_summary(transaction: Dict) -> str:
    """
    Generate a human-readable summary of a transaction
    """
    amount = format_currency(transaction['amount'])
    category = transaction.get('predicted_category', 'Uncategorized')
    confidence = transaction.get('confidence_score', 0) * 100
    
    return (
        f"Transaction: {amount} in category '{category}' "
        f"(AI confidence: {confidence:.1f}%)\n"
        f"Description: {transaction.get('description', 'No description')}"
    )