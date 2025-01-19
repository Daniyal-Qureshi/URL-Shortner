from datetime import datetime
from fastapi import HTTPException, Depends, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import timedelta
from models.models import User
from schemas.Schemas import UserBody
from config.config import SECRET_KEY, ALGORITHM, oauth2_scheme

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def register_user(self,user: UserBody) -> User:
        db_user = self.db.query(User).filter(User.username == user.username).first()
        if db_user:
            raise ValueError("username already registered")
        
        hashed_password = pwd_context.hash(user.password)
        new_user = User(username=user.username, password=hashed_password)
        self.db.add(new_user)
        self.db.commit()
        self.db.refresh(new_user)
        return new_user

    def authenticate_user(self,user: UserBody):
        db_user = self.db.query(User).filter(User.username == user.username).first()
        if not db_user or not self.verify_password(user.password, db_user.password):
            raise ValueError("Invalid credentials")
        
        token_payload = {"username": user.username}
        token = jwt.encode(token_payload, SECRET_KEY, algorithm=ALGORITHM)
        
        return {"access_token": token, "token_type": "bearer", "user_id": db_user.id, "username": db_user.username}

    def verify_password(self,plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def get_current_user(self,token: str = Depends(oauth2_scheme)):
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username = payload.get("username")
            user = self.db.query(User).filter(User.username == username).first()   
            if username is None or user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not validate credentials",
                ) 
            return user
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e)
            )
