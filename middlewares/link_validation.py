from fastapi import Depends, HTTPException, Request
from config.config import get_db
from models.models import Link as LinkModel

def validate_link_middleware(request: Request, db=Depends(get_db)):
    link_id = request.path_params.get('link_id', '')
    short_url = request.path_params.get('short_url', '')
    user_id = False
    if request.get("state", False) and request.get("state").get("user", False):
        user_id = request.state.user.id
    query = db.query(LinkModel).filter(LinkModel.expired == False)
    if user_id:
        query = query.filter(LinkModel.user_id == user_id)
    if link_id:
        query = query.filter(LinkModel.id == link_id)
    elif short_url:
        query = query.filter(LinkModel.short_url == short_url)
    else:
        raise HTTPException(status_code=400, detail="Neither link ID nor short URL provided")

    link = query.first()

    if not link:
        raise HTTPException(status_code=404, detail="Link not found or does not belong to the user")
    
    return link
