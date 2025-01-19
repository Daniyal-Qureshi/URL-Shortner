from fastapi import Depends, Request, HTTPException
from config.config import get_db
from services.auth_service import AuthService

async def validate_user_middleware(request: Request, db = Depends(get_db)):
    try:
        token = request.headers.get("Authorization")   
        if not token:
            raise HTTPException(status_code=401, detail="Authorization token missing")
        token = token.split(" ")[1]
        auth_service = AuthService(db)
        user = auth_service.get_current_user(token=token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))
    
    request.state.user = user
    return user