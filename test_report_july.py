from app import create_app
from services.reports import get_weekly_stats
from datetime import datetime

app = create_app()

with app.app_context():
    print("Generating stats for July 2025...")
    start_date = datetime(2025, 7, 1)
    end_date = datetime(2025, 7, 31, 23, 59, 59)
    
    stats = get_weekly_stats(start_date=start_date, end_date=end_date)
    
    print("-" * 30)
    print(f"Period: {stats['start_date']} - {stats['end_date']}")
    print(f"Total Queries: {stats['total_queries']}")
    print(f"Sold: {stats['sold_queries']}")
    print(f"Lost: {stats['lost_queries']}")
    print(f"Pending: {stats['pending_queries']}")
    print(f"Avg Response Time: {stats['avg_response_time']} hours")
