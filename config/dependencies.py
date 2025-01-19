from fastapi import Depends
from requests import Session
from config.config import get_db
from services.auth_service import AuthService
from services.link_service import LinkService
from services.click_service import ClickService

def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)

def get_link_service(db: Session = Depends(get_db)) -> LinkService:
    return LinkService(db)

def get_click_service(db: Session = Depends(get_db)) -> ClickService:
    return ClickService(db)