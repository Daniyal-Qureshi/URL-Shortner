from datetime import datetime, timedelta, timezone
from typing import List
from fastapi import HTTPException
from models.models import User as UserModel, Link as LinkModel, Click as ClickModel
from sqlalchemy import  func

def clicks_by_day(db):
    start_date, end_date, query = get_day_data(db)
    daily_clicks = []
    
    current_date = end_date
    while current_date >= start_date:
        # Format the current_date as per the expected output
        formatted_date = current_date.strftime('%Y-%m-%d')

        clicks_count = next((clicks for date, clicks in query if date == formatted_date), 0)

        # Append the daily click data to the list
        daily_clicks.append({
            "date": formatted_date,
            "clicks": clicks_count
        })

        # Move to the previous day
        current_date -= timedelta(days=1)

    result = {
        "unit_reference": datetime.now(),
        "link_clicks": daily_clicks,
        "units": len(daily_clicks),
        "unit": "day"
    }

    return result

def clicks_by_month(db):
    start_date, end_date, query = get_month_data(db)
    total_clicks = 0
    
    for date, clicks in query:
        total_clicks+= clicks

    result = {
        "unit_reference": datetime.now(),
        "link_clicks": [{
            "date": start_date,
            "clicks": total_clicks
            
        }],
        "units": "1",
        "unit": "month"
    }
    
    return result


def clicks_by_week(db):
    start_date, end_date, query = get_week_data(db)
    weekly_clicks = []
    query_dict = {result[0]: result[1] for result in query}

    current_date = end_date
    total_weeks = 0
    while current_date >= start_date:
        week_start = current_date - timedelta(days=current_date.weekday())
        week_start_str = week_start.strftime('%Y-%m-%dT00:00:00+0000')
        

        week_end = week_start + timedelta(days=6)
        weekly_clicks.append({
            "date": week_start_str,
            "clicks": sum(clicks for date, clicks in query_dict.items() if week_start <= datetime.strptime(date, '%Y-%m-%dT%H:%M:%S+0000') <= week_end)
        })

        # Move to the previous week
        current_date -= timedelta(weeks=1)
        total_weeks += 1

    result = {
        "unit_reference": datetime.now().strftime('%Y-%m-%dT%H:%M:%S%z'),
        "link_clicks": weekly_clicks,
        "units": total_weeks,
        "unit": "week"
    }
    
    return result

def clicks_by_hour(db):
    start_date, end_date, query = get_hour_data(db)
    hourly_clicks = []
    query_dict = {result[0]: result[1] for result in query}

    current_time = end_date
    total_hours = 0
    while current_time >= start_date:
        hour_str = current_time.strftime('%Y-%m-%d %H:00:00')
        clicks = query_dict.get(hour_str, 0)
        hourly_clicks.append({
            "date": hour_str,
            "clicks": clicks
        })
        current_time -= timedelta(hours=1)
        total_hours += 1

    result = {
        "unit_reference": datetime.now().strftime('%Y-%m-%dT%H:%M:%S%z'),
        "link_clicks": hourly_clicks,
        "units": total_hours,
        "unit": "hour"
    }
    
    return result

def clicks_by_minute(db):
    start_date, end_date, query = get_last_60_minutes_data(db)
    minute_clicks = []
    query_dict = {result[0]: result[1] for result in query}

    current_date = end_date
    total_minutes = 0
    while current_date >= start_date:
        minute_str = current_date.strftime('%Y-%m-%dT%H:%M:00+0000')
        clicks = query_dict.get(minute_str, 0)

        minute_clicks.append({
            "date": minute_str,
            "clicks": clicks
        })

        current_date -= timedelta(minutes=1)
        total_minutes += 1

    result = {
        "unit_reference": datetime.now(),
        "link_clicks": minute_clicks,
        "units": total_minutes,
        "unit": "minute"
    }
    
    return result

def get_last_60_minutes_data(db):
    end_date = datetime.now()
    start_date = end_date - timedelta(minutes=59)  # Last 60 minutes
    query = last_60_minutes_query(db, start_date, end_date)
    
    return start_date, end_date, query

def last_60_minutes_query(db, start_date, end_date):
    return db.query(
        func.strftime('%Y-%m-%dT%H:%M:00+0000', ClickModel.timestamp).label('timestamp'),
        func.count().label('total_clicks')
    ).filter(
        ClickModel.timestamp >= start_date,
        ClickModel.timestamp <= end_date
    ).group_by(
        func.strftime('%Y-%m-%dT%H:%M:00+0000', ClickModel.timestamp)
    ).order_by(
        func.strftime('%Y-%m-%dT%H:%M:00+0000', ClickModel.timestamp)
    ).all()



def get_week_data(db):
    end_date = datetime.now()
    start_date = end_date - timedelta(weeks=6)  
    query = week_query(db, start_date, end_date)
    return start_date, end_date, query

def get_hour_data(db):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=45)  # 45 days back
    query = hour_query(db, start_date, end_date)
    
    return start_date, end_date, query


def get_day_data(db):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=44)  
    query = day_and_month_query(db, start_date, end_date)
    
    return start_date, end_date, query


def get_month_data(db):
    end_date = datetime.now()
    start_date = datetime(end_date.year, end_date.month, 1)  
    query = day_and_month_query(db, start_date, end_date)
    return start_date, end_date, query


def week_query(db, start_date, end_date):
    return db.query(
        func.strftime('%Y-%m-%dT%H:%M:%S+0000', ClickModel.timestamp).label('timestamp'),
        func.count().label('total_clicks')
    ).filter(
        ClickModel.timestamp >= start_date,
        ClickModel.timestamp <= end_date
    ).group_by(
        func.strftime('%Y-%m-%dT%H:%M:%S+0000', ClickModel.timestamp)
    ).order_by(
        func.strftime('%Y-%m-%dT%H:%M:%S+0000', ClickModel.timestamp)
    ).all()


def day_and_month_query(db, start_date,end_date):
    return db.query(
        func.date(ClickModel.timestamp).label('day'),
        func.count().label('total_clicks')
    ).filter(
        ClickModel.timestamp >= start_date,
        ClickModel.timestamp <= end_date
    ).group_by(
        func.date(ClickModel.timestamp)
    ).all()


def hour_query(db, start_date, end_date):
    return db.query(
        func.strftime('%Y-%m-%d %H:00:00', ClickModel.timestamp).label('hour'),
        func.count().label('total_clicks')
    ).filter(
        ClickModel.timestamp >= start_date,
        ClickModel.timestamp <= end_date
    ).group_by(
        func.strftime('%Y-%m-%d %H:00:00', ClickModel.timestamp)
    ).order_by(
        func.strftime('%Y-%m-%d %H:00:00', ClickModel.timestamp)
    ).all()

