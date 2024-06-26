from fastapi import APIRouter, HTTPException, Depends, status, Query, Response, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Optional, List
from fastapi import BackgroundTasks
from pydantic import BaseModel
from fastapi.responses import RedirectResponse
import requests
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from utils.helper import *
from utils.click_utils import *
from models.models import User as UserModel, Link as LinkModel, Click as ClickModel
from requests.exceptions import HTTPError, JSONDecodeError
from sqlalchemy.orm import joinedload
from schemas.Schemas import (
    User as UserSchema,
    Link as LinkSchema,
    ClicksSummary,
    ClicksSummaryByCountry,
    ShareTribeUserResponse,
)
from config.config import logger, SECRET_KEY, ALGORITHM, oauth2_scheme, REDIRECT_URL
router = APIRouter()

class ShortenLinkRequest(BaseModel):
    title: str
    long_url: str
    custom_back_half: Optional[str] = None


@router.get("/{short_url}")
async def redirect_to_long_url(
    short_url: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    link = db.query(LinkModel).filter(LinkModel.short_url == short_url).first()
    if link is None:
        raise HTTPException(status_code=404, detail="Link not found")
    if link.expired:
        raise HTTPException(status_code=410, detail="Link has expired")

    long_url = link.long_url
    user_agent = request.headers.get("user-agent", "unknown")
    ip_address = request.headers.get("CF-Connecting-IP", None)
    if not ip_address:
        ip_address = request.client.host
    click = ClickModel(link_id=link.id, user_agent=user_agent, ip=ip_address)
    db.add(click)
    db.commit()
    background_tasks.add_task(write_ip_info, click.id, ip_address, db)

    if not long_url.startswith(("http://", "https://")):
        long_url = "http://" + long_url
    return RedirectResponse(url=long_url)


@router.post("/v1/auth/token")
async def authenticate(
    formdata: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    logger.info("Authenticating user")
    logger.debug(f"Username: {formdata.username}")
    username = formdata.username
    password = formdata.password
    url = "https://flex-api.sharetribe.com/v1/auth/token"
    payload = {
        "client_id": "dc31b12f-8294-4e24-b027-24ce590ffd16",
        "grant_type": "password",
        "username": username,
        "password": password,
        "scope": "user",
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
        "Accept": "application/json",
    }
    
    try:
        response = requests.post(url, data=payload, headers=headers)
        response.raise_for_status()
        external_api_response = response.json()
        print(external_api_response)

        # if the user exist in the database then return a new jwt token
        user = db.query(UserModel).filter(UserModel.username == username).first()
        if user:
            token_payload = {"username": username}
            user.external_api_token = external_api_response["access_token"]
            db.commit()
            token = jwt.encode(token_payload, SECRET_KEY, algorithm=ALGORITHM)
            return {
                "id": user.id,
                "username": username,
                "access_token": token,
                "token_type": "bearer",
            }
        else:
            user = UserModel(
                username=username,
                external_api_token=external_api_response["access_token"],
            )
            db.add(user)
            db.commit()
            token_payload = {"username": username}
            token = jwt.encode(token_payload, SECRET_KEY, algorithm=ALGORITHM)
            return {
                "id": user.id,
                "username": username,
                "access_token": token,
                "token_type": "bearer",
            }

    except HTTPError as http_err:
        raise HTTPException(
            status_code=http_err.response.status_code, detail=http_err.response.text
        )
    except JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid JSON response from server")
    except KeyError:
        raise HTTPException(status_code=500, detail="Access token not found in external API response")


@router.get("/api/users/me", response_model=UserSchema)
async def read_users_me(
    current_username: str = Depends(get_current_user), db: Session = Depends(get_db)
):
    user = db.query(UserModel).filter(UserModel.username == current_username).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get("/api/user/details", response_model=ShareTribeUserResponse)
async def get_user_details(
    current_username: str = Depends(get_current_user), db: Session = Depends(get_db)
):
    user = db.query(UserModel).filter(UserModel.username == current_username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    access_token = user.external_api_token
    if not access_token:
        raise HTTPException(
            status_code=400, detail="User does not have an access token"
        )

    url = "https://flex-api.sharetribe.com/v1/api/current_user/show"
    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    query = {
        "include": "profileImage",
        "fields.image": "variants.square-small,variants.square-small2x",
    }

    try:
        response = requests.get(url, headers=headers, params=query)
        response.raise_for_status()
        user_details = response.json()
        return user_details
    except HTTPError as http_err:
        raise HTTPException(
            status_code=http_err.response.status_code, detail=http_err.response.text
        )
    except JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid JSON response from server")
    except KeyError:
        raise HTTPException(status_code=500, detail="Error fetching user details")

@router.get("/api/users/{user_id}/links", response_model=List[LinkSchema])
async def get_user_links(
    user_id: int,
    current_username: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.username != current_username:
        raise HTTPException(
            status_code=403, detail="Not authorized to view this user's links"
        )
    links = (
        db.query(LinkModel)
        .options(joinedload(LinkModel.owner))
        .filter(LinkModel.owner.has(id=user_id))
        .all()
    )
    return links

@router.post("/api/shorten")
async def shorten_link(
    request: ShortenLinkRequest,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    user = validate_user(token=token, db=db)
    link = db.query(LinkModel).filter(LinkModel.long_url == request.long_url, LinkModel.user_id == user.id).first()
    if link:
        return {
            "link": link.bitlink, 
            "title": link.title,
            "long_url": link.long_url,
            "id":link.short_url,
            "created_at": link.created_at
            }
    
    title = request.title
    long_url = request.long_url
    
    if request.custom_back_half:
        short_url = request.custom_back_half
        if is_link_exist(db, short_url):
            raise HTTPException(status_code=409, detail="Custom short URL already exists")
    
    else:
        short_url = create_unique_short_url(db)
    
    bitlink = f'{REDIRECT_URL}/{short_url}'

    new_link = LinkModel(
        bitlink=bitlink, owner=user, expired=False, long_url=long_url, title=title, short_url=short_url
    )
    db.add(new_link)
    db.commit()
    db.refresh(new_link)

    return {
            "link": bitlink, 
            "title": title,
            "long_url": long_url,
            "id":short_url,
            "created_at": datetime.now()
            }

@router.delete("/api/bitlinks/{link_id}")
async def delete_bitlink(
    link_id: int,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    user = validate_user(token=token, db=db)
    db_link = validate_link(link_id=link_id, db=db, user=user)

    db_link.expired = True
    db.commit()
    return {"message": "Link successfully deleted"}


@router.get("/api/bitlinks/{link_id}/clicks/unique", response_model=dict)
async def get_unique_clicks(
    link_id: str,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    user = validate_user(token=token, db=db)
    validate_link(link_id=link_id, db=db, user=user)
    
    clicks = db.query(ClickModel).filter(ClickModel.link_id == link_id).all()
    unique_combinations = {}
    unique_clicks_info = []
    

    for click in clicks:
        combination = (click.ip, click.user_agent)
        ip_info = get_click_ip_info(click.id, db)
        if combination not in unique_combinations:
            # Add the combination to the dictionary with its timestamp
            unique_combinations[combination] = click.timestamp
                
            unique_clicks_info.append({
                "ip": click.ip,
                "user_agent": click.user_agent,
                "timestamp": click.timestamp,
                **ip_info
            })
        else:
            # Check if the current click is within the threshold of the previous click with the same combination
            if click.timestamp > unique_combinations[combination] + timedelta(hours=12):
                # Update the timestamp in the dictionary to the latest click's timestamp
                unique_combinations[combination] = click.timestamp
                
                unique_clicks_info.append({
                    "ip": click.ip,
                    "user_agent": click.user_agent,
                    "timestamp": click.timestamp,
                    **ip_info
                })

    return {
        "unique_clicks": unique_clicks_info,
        "total_unique_clicks": len(unique_clicks_info)
    }


@router.get("/api/bitlinks/{link_id}/clicks", response_model=ClicksSummary)
async def get_clicks(
    link_id: str,
    response: Response,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    unit: str = Query("day", enum=["minute", "hour", "day", "week", "month"]),
    units: int = Query(-1),
    unit_reference: Optional[str] = None,
):
   
    user = validate_user(token=token, db=db)
    validate_link(link_id=link_id, db=db, user=user)
    
    if unit == "minute":
        return clicks_by_minute(db)
    elif unit == "hour":
        return clicks_by_hour(db)
    elif unit == "day":
        return clicks_by_day(db)
    elif unit == "week":
        return clicks_by_week(db)
    elif unit == "month":
        return clicks_by_month(db)
    else:
        raise HTTPException(status_code=400, detail="Invalid unit specified")


@router.get("/api/bitlinks")
async def get_user_links(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user = validate_user(token=token, db=db)
    links = db.query(LinkModel).filter(LinkModel.owner == user).all()
    return links


@router.get("/api/bitlinks/{link_id}/countries", response_model=ClicksSummaryByCountry)
async def get_clicks_by_country(
    link_id: str,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
   
    user = validate_user(token=token, db=db)
    validate_link(link_id=link_id, db=db, user=user)

    clicks = db.query(ClickModel).filter(ClickModel.link_id == link_id).all()
        
    country_clicks = {}
    for click in clicks:
        country = get_country_clicks(db, click.id)
        if country:
            if country in country_clicks:
                country_clicks[country]["clicks"] += 1
            else:
                country_clicks[country] = {"value": country, "clicks": 1}

    metrics = [{"value": v["value"], "clicks": v["clicks"]} for v in country_clicks.values()]

    return {
        "unit_reference": datetime.now(),
        "metrics": metrics,
        "units": len(clicks),
        "unit": "day",
        "facet": "countries"
    }

@router.get("/api/bitlinks/{link_id}", response_model=LinkSchema)
async def get_bitlink(
    link_id: str,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    user = get_db_user(token=token, db=db)
    db_link =validate_link(link_id=link_id, db=db, user=user)
    return db_link


@router.get("/")
def index():
    return {"message": "Welcome to Microsh URL shortener"}
