from fastapi import APIRouter, HTTPException, Depends, status, Query, Response, Request
from sqlalchemy.orm import Session
from fastapi.responses import RedirectResponse
from datetime import datetime
from models.models import User as UserModel, Link as LinkModel, Click as ClickModel
from config.dependencies import get_click_service
from config.config import oauth2_scheme
from services.click_service import ClickService
from middlewares.link_validation import validate_link_middleware 
from middlewares.user_validation import validate_user_middleware
from fastapi import BackgroundTasks
from typing import Optional, List
from schemas.Schemas import (
    User as UserSchema,
    Link as LinkSchema,
    ClicksSummary,
    ClicksSummaryByCountry,
    ShortenLinkResponse,
    ShortenLinkRequest
)

router = APIRouter()

@router.get("/api/bitlinks/{link_id}/clicks", response_model=ClicksSummary)
async def get_clicks(
    link_id: int,
    token: str = Depends(oauth2_scheme),
    user = Depends(validate_user_middleware), 
    link = Depends(validate_link_middleware),  
    unit: str = Query("day", enum=["minute", "hour", "day", "week", "month"]),
    click_service: ClickService = Depends(get_click_service),
):
       
    if unit == "minute":
        return click_service.clicks_by_minute(link_id)
    elif unit == "hour":
        return click_service.clicks_by_hour(link_id)
    elif unit == "day":
        return click_service.clicks_by_day(link_id)
    elif unit == "week":
        return click_service.clicks_by_week(link_id)
    elif unit == "month":
        return click_service.clicks_by_month(link_id)
    else:
        raise HTTPException(status_code=400, detail="Invalid unit specified")
    
@router.get("/api/bitlinks/{link_id}/countries", response_model=ClicksSummaryByCountry)
async def get_clicks_by_country(
    link_id: int,
    token: str = Depends(oauth2_scheme),
    user = Depends(validate_user_middleware), 
    link = Depends(validate_link_middleware),  
    click_service: ClickService = Depends(get_click_service),
):
   return click_service.clicks_by_country(link_id)