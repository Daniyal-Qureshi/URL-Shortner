from requests import Session
import requests
from fastapi import HTTPException, Depends, status
from jose import JWTError, jwt
import string
import random
from models.models import Link, User, IPInfo as IPInfoModel, Link as LinkModel, Click as ClickModel
from sqlalchemy.orm import Session
from config.config import logger ,get_db, REDIRECT_URL
from datetime import timedelta ,datetime
from sqlalchemy import  func
from services.ip_info_service import IPInfoService

class LinkService:
    def __init__(self, db: Session):
        self.db = db
        self.ip_info_service = IPInfoService(db)
        
    def get_unique_clicks(self, link_id: int):
        clicks = self.db.query(ClickModel).filter(ClickModel.link_id == link_id).all()
        unique_combinations = {}
        unique_clicks_info = []
        
        for click in clicks:
            combination = (click.ip, click.user_agent)
            ip_info = self.ip_info_service.get_click_ip_info(click.id)
            if combination not in unique_combinations:
                unique_combinations[combination] = click.timestamp
                    
                unique_clicks_info.append({
                    "ip": click.ip,
                    "user_agent": click.user_agent,
                    "timestamp": click.timestamp,
                    **ip_info
                })
            else:
                if click.timestamp > unique_combinations[combination] + timedelta(hours=12):
                    unique_combinations[combination] = click.timestamp
                    
                    unique_clicks_info.append({
                        "ip": click.ip,
                        "user_agent": click.user_agent,
                        "timestamp": click.timestamp,
                        **ip_info
                    })
        return unique_clicks_info
        
  
    def is_link_exist(self, short_url):
        return self.db.query(Link).filter(Link.short_url == short_url).first()
    
    def generate_short_url(self,length=7):
        characters = string.ascii_letters + string.digits
        return ''.join(random.choice(characters) for i in range(length))

    def create_unique_short_url(self):
        tries = 0
        max_tries = 2
        url_length = 7

        while tries < max_tries:
            short_url = self.generate_short_url(url_length)
            existing_link = self.is_link_exist(short_url)

            if not existing_link:
                return short_url
            tries += 1
            
        return self.generate_short_url(url_length + 1)
    
    def get_user_active_links(self, user):
        query = self.db.query(LinkModel).filter(LinkModel.owner == user, LinkModel.expired == False)    
        return query.all()

    def redirect_to_url(self,link, request, background_tasks):
        long_url = link.long_url
        user_agent = request.headers.get("user-agent", "unknown")
        ip_address = request.headers.get("CF-Connecting-IP", None)
        if not ip_address:
            ip_address = request.client.host
        click = ClickModel(link_id=link.id, user_agent=user_agent, ip=ip_address)
        self.db.add(click)
        self.db.commit()
        background_tasks.add_task(self.ip_info_service.write_ip_info, click.id, ip_address)
        
        if not long_url.startswith(("http://", "https://")):
            long_url = "http://" + long_url
   
    def delete_link(self, link):
        link.expired = True
        self.db.commit()
    
    def shorten_url(self, body, user):
        title = body.title
        long_url = body.long_url
        custom_balk_half = body.custom_back_half
        
        link = self.db.query(LinkModel).filter(LinkModel.long_url == long_url, LinkModel.user_id == user.id).first()
        if link:
            return {
                "link": link.bitlink, 
                "title": link.title,
                "long_url": link.long_url,
                "id":link.id,
                "created_at": link.created_at
                }
    
        if custom_balk_half:
            short_url = custom_balk_half
            if self.is_link_exist(short_url):
                raise HTTPException(status_code=409, detail="Custom short URL already exists")
        
        else:
            short_url = self.create_unique_short_url()
        
        bitlink = f'{REDIRECT_URL}/{short_url}'

        new_link = LinkModel(
            bitlink=bitlink, owner=user, expired=False, long_url=long_url, title=title, short_url=short_url
        )
        self.db.add(new_link)
        self.db.commit()
        self.db.refresh(new_link)

        return {
                "link": bitlink, 
                "title": title,
                "long_url": long_url,
                "id":new_link.id,
                "created_at": datetime.now()
                }