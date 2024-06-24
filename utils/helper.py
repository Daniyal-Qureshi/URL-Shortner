import requests
from fastapi import HTTPException, Depends, status
from jose import JWTError, jwt
from config.config import SECRET_KEY, ALGORITHM, oauth2_scheme, DATABASE_URL, SessionLocal
import string
import random
from models.models import Link, User
from sqlalchemy.orm import Session

def get_ip_info(ip_address):
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
            "readme": data.get("readme")
        }
    else:
        return {"error": "Unable to retrieve data"}
    

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


def generate_short_url(length=7):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for i in range(length))

def create_unique_short_url(db: Session):
    tries = 0
    max_tries = 2
    url_length = 7

    while tries < max_tries:
        short_url = generate_short_url(url_length)
        existing_link = db.query(Link).filter(Link.short_url == short_url).first()

        if not existing_link:
            return short_url
        tries += 1

    # If we exceed the max_tries, increase the length of the URL
    return generate_short_url(url_length + 1)