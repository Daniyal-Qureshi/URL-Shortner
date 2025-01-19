from datetime import datetime, timedelta, timezone
from typing import List
from fastapi import HTTPException
from requests import Session
from models.models import User as UserModel, Link as LinkModel, Click as ClickModel
from sqlalchemy import  func
from models.models import IPInfo as IPInfoModel

class ClickService:
    def __init__(self, db: Session):
        self.db = db
        
    def clicks_by_country(self, link_id):     
        clicks = self.db.query(ClickModel).filter(ClickModel.link_id == link_id).all()
            
        country_clicks = {}
        for click in clicks:
            country_record = self.db.query(IPInfoModel).filter(IPInfoModel.click_id == click.id).first()
            country = country_record.country if country_record else None
            if country:
                if country in country_clicks:
                    country_clicks[country]["clicks"] += 1
                else:
                    country_clicks[country] = {"value": country, "clicks": 1}

        metrics = [{"value": v["value"], "clicks": v["clicks"]} for v in country_clicks.values()]

        return {
            "unit_reference": datetime.now(),
            "metrics": metrics,
            "units": len(clicks),
            "unit": "day",
            "facet": "countries"
        }
            
    def clicks_by_day(self, link_id):
        start_date, end_date, query = self.get_day_data(link_id)
        daily_clicks = []
        
        current_date = end_date
        while current_date >= start_date:
            # Format the current_date as per the expected output
            formatted_date = current_date.strftime('%Y-%m-%d')

            clicks_count = next((clicks for date, clicks in query if date == formatted_date), 0)
            
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

    def clicks_by_month(self, link_id):
        start_date, end_date, query = self.get_month_data(link_id)
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


    def clicks_by_week(self, link_id):
        start_date, end_date, query = self.get_week_data(link_id)
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

    def clicks_by_hour(self, link_id):
        start_date, end_date, query = self.get_hour_data(link_id)
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

    def clicks_by_minute(self, link_id):
        start_date, end_date, query = self.get_last_60_minutes_data(db, link_id)
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

    def get_last_60_minutes_data(self, link_id):
        end_date = datetime.now()
        start_date = end_date - timedelta(minutes=59) 
        query = self.last_60_minutes_query(start_date, end_date, link_id)
        
        return start_date, end_date, query

    def last_60_minutes_query(self, start_date, end_date, link_id):
        return self.db.query(
            func.strftime('%Y-%m-%dT%H:%M:00+0000', ClickModel.timestamp).label('timestamp'),
            func.count().label('total_clicks')
        ).filter(
            ClickModel.timestamp >= start_date,
            ClickModel.timestamp <= end_date,
            ClickModel.link_id == link_id
        ).group_by(
            func.strftime('%Y-%m-%dT%H:%M:00+0000', ClickModel.timestamp)
        ).order_by(
            func.strftime('%Y-%m-%dT%H:%M:00+0000', ClickModel.timestamp)
        ).all()



    def get_week_data(self, link_id):
        end_date = datetime.now()
        start_date = end_date - timedelta(weeks=6)  
        query = self.week_query(start_date, end_date, link_id)
        return start_date, end_date, query

    def get_hour_data(db, link_id):
        end_date = datetime.now()
        start_date = end_date - timedelta(days=45)  # 45 days back
        query = self.hour_query( start_date, end_date, link_id)
        
        return start_date, end_date, query


    def get_day_data(self, link_id):
        end_date = datetime.now()
        start_date = end_date - timedelta(days=44)  
        query = self.day_and_month_query(start_date, end_date, link_id)
        
        return start_date, end_date, query


    def get_month_data(self, link_id):
        end_date = datetime.now()
        start_date = datetime(end_date.year, end_date.month, 1)  
        query = self.day_and_month_query(start_date, end_date, link_id)
        return start_date, end_date, query


    def week_query(self, start_date, end_date, link_id):
        return self.db.query(
            func.strftime('%Y-%m-%dT%H:%M:%S+0000', ClickModel.timestamp).label('timestamp'),
            func.count().label('total_clicks')
        ).filter(
            ClickModel.timestamp >= start_date,
            ClickModel.timestamp <= end_date,
            ClickModel.link_id == link_id
        ).group_by(
            func.strftime('%Y-%m-%dT%H:%M:%S+0000', ClickModel.timestamp)
        ).order_by(
            func.strftime('%Y-%m-%dT%H:%M:%S+0000', ClickModel.timestamp)
        ).all()


    def day_and_month_query(self, start_date,end_date, link_id):
        return self.db.query(
            func.date(ClickModel.timestamp).label('day'),
            func.count().label('total_clicks')
        ).filter(
            ClickModel.timestamp >= start_date,
            ClickModel.timestamp <= end_date,
            ClickModel.link_id == link_id
        ).group_by(
            func.date(ClickModel.timestamp)
        ).all()


    def hour_query(self, start_date, end_date, link_id):
        return self.db.query(
            func.strftime('%Y-%m-%d %H:00:00', ClickModel.timestamp).label('hour'),
            func.count().label('total_clicks')
        ).filter(
            ClickModel.timestamp >= start_date,
            ClickModel.timestamp <= end_date,
            ClickModel.link_id == link_id
        ).group_by(
            func.strftime('%Y-%m-%d %H:00:00', ClickModel.timestamp)
        ).order_by(
            func.strftime('%Y-%m-%d %H:00:00', ClickModel.timestamp)
        ).all()

