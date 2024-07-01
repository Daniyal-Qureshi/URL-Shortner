import requests
from fastapi import HTTPException, Depends, status
from jose import JWTError, jwt
from config.config import SECRET_KEY, ALGORITHM, oauth2_scheme, DATABASE_URL, SessionLocal
import string
import random
from models.models import Link, User, IPInfo as IPInfoModel, Link as LinkModel
from sqlalchemy.orm import Session
from config.config import logger
from sqlalchemy import  func

def get_ip_info_API(ip_address):
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

def write_ip_info(click_id, ip, db: Session):
    try:
        ip_response = get_ip_info_API(ip)
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
        db.add(ip_info)
        db.commit()
        db.close()
        logger.info(f"IPInfo created successfully for click_id {click_id} with ip {ip}")
    except Exception as e:
        logger.info(f"Error creating IPInfo for click_id {click_id} with ip {ip}. Error: {e}")


def get_click_ip_info(click_id, db: Session):
    ip_info = db.query(IPInfoModel).filter(IPInfoModel.click_id == click_id).first()
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

def get_country_clicks(db: Session, click_id: int):
    return db.query(IPInfoModel).filter(IPInfoModel.click_id == click_id).first().country

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("username")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )
        return username
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

def get_db_user(username = "", token: str = Depends(oauth2_scheme), db = Session):
    username = get_current_user(token) if token else username
    return db.query(User).filter(User.username == username).first()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def is_link_exist(db, short_url):
    return db.query(Link).filter(Link.short_url == short_url).first()


def generate_short_url(length=7):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for i in range(length))

def create_unique_short_url(db: Session):
    tries = 0
    max_tries = 2
    url_length = 7

    while tries < max_tries:
        short_url = generate_short_url(url_length)
        existing_link = is_link_exist(db, short_url)

        if not existing_link:
            return short_url
        tries += 1

    # If we exceed the max_tries, increase the length of the URL
    return generate_short_url(url_length + 1)

def validate_link(link_id, user,  db: Session):
    db_link = (
        db.query(LinkModel)
        .filter(LinkModel.id == link_id, LinkModel.owner == user)
        .first()
    )
    if not db_link:
        raise HTTPException(status_code=404, detail="Link not found")
    if db_link.expired:
        raise HTTPException(status_code=400, detail="Link has expired")
    return db_link
 
def validate_user(token, db: Session):
    user = get_db_user(token=token, db=db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def get_user_links(db, user, expired=True):
    query = db.query(LinkModel).filter(LinkModel.owner == user)
    
    if not expired:
        query = query.filter(LinkModel.expired == expired)
    
    return query.all()