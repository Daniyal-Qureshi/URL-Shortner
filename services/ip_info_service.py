from requests import Session
import requests
from fastapi import HTTPException, Depends, status
from jose import JWTError, jwt
from config.config import SECRET_KEY, ALGORITHM, oauth2_scheme, DATABASE_URL, SessionLocal
import string
import random
from models.models import Link, User, IPInfo as IPInfoModel, Link as LinkModel, Click as ClickModel
from sqlalchemy.orm import Session
from config.config import logger ,get_db
from sqlalchemy import  func

class IPInfoService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_ip_info_API(self,ip_address):
        url = f"https://ipinfo.io/{ip_address}/json"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return {
                "ip": data.get("ip"),
                "city": data.get("city"),
                "region": data.get("region"),
                "country": data.get("country"),
                "loc": data.get("loc"),
                "org": data.get("org"),
                "postal": data.get("postal"),
                "timezone": data.get("timezone"),
            }
        else:
            return {"error": "Unable to retrieve data"}

    def write_ip_info(self,click_id, ip):
        try:
            ip_response = self.get_ip_info_API(ip)
            ip_info = IPInfoModel(
                ip=ip,
                click_id=click_id, 
                country=ip_response['country'],
                city=ip_response['city'],
                region=ip_response['region'],
                loc = ip_response['loc'],
                timezone=ip_response['timezone'],
                org=ip_response['org'],
                postal=ip_response['postal']
                )
            self.db.add(ip_info)
            self.db.commit()
            self.db.close()
            logger.info(f"IPInfo created successfully for click_id {click_id} with ip {ip}")
        except Exception as e:
            logger.info(f"Error creating IPInfo for click_id {click_id} with ip {ip}. Error: {e}")


    def get_click_ip_info(self,click_id):
        ip_info = self.db.query(IPInfoModel).filter(IPInfoModel.click_id == click_id).first()
        if not ip_info:
            return {"error": "No IP info found"}
        return {
            "ip": ip_info.ip,
            "city": ip_info.city,
            "region": ip_info.region,
            "country": ip_info.country,
            "loc": ip_info.loc,
            "org": ip_info.org,
            "postal": ip_info.postal,
            "timezone": ip_info.timezone,
        }
