from fastapi import APIRouter, HTTPException, Depends, status, Query, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from models.models import User as UserModel, Link as LinkModel, Click as ClickModel
from schemas.Schemas import (
    UserBody,
    Token
)
from config.dependencies import  get_auth_service
from services.auth_service import AuthService
from config.config import oauth2_scheme, SECRET_KEY, ALGORITHM, get_db

router = APIRouter()

@router.post("/register")
async def register_user_route(
    user: UserBody,
    auth_service: AuthService = Depends(get_auth_service),
     db: Session = Depends(get_db),
):
    try:
        new_user = auth_service.register_user(user)
        return new_user
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login", response_model=Token)
async def authenticate(
    formdata: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
     db: Session = Depends(get_db),
):
    
    try:
        user  = UserBody(username=formdata.username, password=formdata.password)
        token = auth_service.authenticate_user(user)
        return token
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))



