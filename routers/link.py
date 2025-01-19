from fastapi import APIRouter, HTTPException, Depends, status, Query, Response, Request
from sqlalchemy.orm import Session
from fastapi.responses import RedirectResponse
from datetime import datetime
from models.models import User as UserModel, Link as LinkModel, Click as ClickModel
from config.dependencies import get_link_service
from services.link_service import LinkService
from middlewares.link_validation import validate_link_middleware 
from middlewares.user_validation import validate_user_middleware
from fastapi import BackgroundTasks
from typing import Optional, List
from schemas.Schemas import (
    User as UserSchema,
    Link as LinkSchema,
    ShortenLinkResponse,
    ShortenLinkRequest
)

from config.config import oauth2_scheme
router = APIRouter()


@router.post("/shorten", response_model=ShortenLinkResponse)
async def shorten_link(
    body: ShortenLinkRequest,
    token: str = Depends(oauth2_scheme),
    user = Depends(validate_user_middleware),
    link_service: LinkService = Depends(get_link_service),
):
    try:
        return link_service.shorten_url(body, user)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/api/bitlinks/{link_id}")
async def delete_bitlink(
    link_id: int,
    token: str = Depends(oauth2_scheme),
    user = Depends(validate_user_middleware), 
    link = Depends(validate_link_middleware),  
    link_service: LinkService = Depends(get_link_service),
):
    try:
        link_service.delete_link(link)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"message": "Link successfully deleted"}


@router.get("/api/bitlinks/{link_id}/clicks/unique", response_model=dict)
async def unique_clicks(
    link_id: int,
    token: str = Depends(oauth2_scheme),
    user = Depends(validate_user_middleware), 
    link = Depends(validate_link_middleware),  
    link_service: LinkService = Depends(get_link_service),
):
    try:   
        unique_clicks_info = link_service.get_unique_clicks(link_id)

        return {
            "unique_clicks": unique_clicks_info,
            "total_unique_clicks": len(unique_clicks_info)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/api/bitlinks/active")
async def get_links_active( 
    token: str = Depends(oauth2_scheme),                    
    user = Depends(validate_user_middleware), 
    link_service: LinkService = Depends(get_link_service),   
):
    try:
        links = link_service.get_user_active_links(user)
        return links
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/bitlinks/{link_id}", response_model=LinkSchema)
async def get_bitlink(
    link_id: int,
    token: str = Depends(oauth2_scheme),
    user = Depends(validate_user_middleware), 
    link = Depends(validate_link_middleware),  
):
    return link
