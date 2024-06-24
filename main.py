from fastapi import FastAPI, HTTPException, Depends, status, Query, Response, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from requests.exceptions import HTTPError, JSONDecodeError
from typing import Optional, List
from pydantic import BaseModel
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from helper import get_ip_info
from models.models import Base, User as UserModel, Link as LinkModel, UniqueClick as ClickModel
from schemas.Schemas import (
    User as UserSchema,
    Link as LinkSchema,
    TotalClicksSummary,
    ClicksSummary,
    ClicksSummaryByCountry,
    ShareTribeUserResponse,
)
import logging
import requests
import os

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logger = logging.getLogger("app")
logger.setLevel(logging.DEBUG)

fh = logging.FileHandler("QED.log")
fh.setLevel(logging.ERROR)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
fh.setFormatter(formatter)
ch.setFormatter(formatter)

logger.addHandler(fh)
logger.addHandler(ch)


DATABASE_URL = "sqlite:///./main.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
REDIRECT_URL = os.getenv("REDIRECT_URL", "http://0.0.0.0:8000")

logger.log(logging.DEBUG, f"Redirect URL: {REDIRECT_URL}")
Base.metadata.create_all(bind=engine)


# JWT Secret Key
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/token")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/v1/auth/token")
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
    # response = requests.post(url, data=payload, headers=headers)

    # return {username, password}
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
        raise HTTPException(
            status_code=500, detail="Access token not found in external API response"
        )


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


@app.get("/api/users/me", response_model=UserSchema)
async def read_users_me(
    current_username: str = Depends(get_current_user), db: Session = Depends(get_db)
):
    user = db.query(UserModel).filter(UserModel.username == current_username).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.get("/api/user/details", response_model=ShareTribeUserResponse)
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


from sqlalchemy.orm import joinedload


@app.get("/api/users/{user_id}/links", response_model=List[LinkSchema])
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


class ShortenLinkRequest(BaseModel):
    title: str
    long_url: str
    domain: Optional[str] = "bit.ly"
    group_guid: Optional[str] = ""


BITLY_API_BASE_URL = "https://api-ssl.bitly.com/v4"
BITLY_ACCESS_TOKEN = "f8d2f422017662bedfebc23a156e40e443be80e1"


def call_bitly_api(endpoint: str, params: dict = {}, method: str = "GET"):
    headers = {
        "Authorization": f"Bearer {BITLY_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    url = f"{BITLY_API_BASE_URL}/{endpoint}"
    if method == "GET":
        response = requests.get(url, headers=headers, params=params)
        print(response.text)
    elif method == "POST":
        response = requests.post(url, headers=headers, json=params)
    elif method == "DELETE":
        response = requests.delete(url, headers=headers, json=params)
    else:
        raise ValueError("Unsupported HTTP method")

    response.raise_for_status()
    return response.json()


@app.delete("/api/bitlinks/{bitlink}")
async def delete_bitlink(
    bitlink: str,
    current_username: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(UserModel).filter(UserModel.username == current_username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db_link = (
        db.query(LinkModel)
        .filter(LinkModel.id == bitlink, LinkModel.owner == user)
        .first()
    )
    if not db_link or db_link.expired:
        raise HTTPException(status_code=404, detail="Link not found")
    
    db_link.expired = True
    db.commit()
    
    return {"message": "Link has been deleted"}

  

@app.get("/api/bitlinks/{bitlink}", response_model=LinkSchema)
async def get_bitlink(
    bitlink: str,
    current_username: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(UserModel).filter(UserModel.username == current_username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db_link = (
        db.query(LinkModel)
        .filter(LinkModel.id == bitlink, LinkModel.owner == user)
        .first()
    )
    if not db_link:
        raise HTTPException(status_code=404, detail="Link not found")

    return db_link


@app.get("/api/bitlinks/{bitlink}/clicks", response_model=ClicksSummary)
async def get_clicks(
    bitlink: str,
    response: Response,
    current_username: str = Depends(get_current_user),
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
    unit: str = Query("day", enum=["minute", "hour", "day", "week", "month"]),
    units: int = Query(-1),
    unit_reference: Optional[str] = None,
):
    user = db.query(UserModel).filter(UserModel.username == current_username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db_link = (
        db.query(LinkModel)
        .filter(LinkModel.id == bitlink, LinkModel.owner == user)
        .first()
    )
    if not db_link:
        raise HTTPException(status_code=404, detail="Link not found")
    # extract domain and hash from bitlink
    domain = db_link.bitlink.split("/")[2]
    hash = db_link.bitlink.split("/")[3]
    params = {"unit": unit, "units": units, "unit_reference": unit_reference}

    # cache for an entire day
    response.headers["Cache-Control"] = "max-age=86400"

    try:
        print("well")
        return call_bitly_api(f"bitlinks/{domain}/{hash}/clicks", params=params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/bitlinks/{bitlink}/summary", response_model=TotalClicksSummary)
async def get_clicks_summary(
    bitlink: str,
    response: Response,
    current_username: str = Depends(get_current_user),
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
    unit: str = Query("day", enum=["minute", "hour", "day", "week", "month"]),
    units: int = Query(-1),
    unit_reference: Optional[str] = None,
):
    user = db.query(UserModel).filter(UserModel.username == current_username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db_link = (
        db.query(LinkModel)
        .filter(LinkModel.id == bitlink, LinkModel.owner == user)
        .first()
    )
    if not db_link:
        raise HTTPException(status_code=404, detail="Link not found")
    # extract domain and hash from bitlink
    domain = db_link.bitlink.split("/")[2]
    hash = db_link.bitlink.split("/")[3]
    params = {"unit": unit, "units": units, "unit_reference": unit_reference}

    # cache for an entire day
    response.headers["Cache-Control"] = "max-age=86400"

    try:
        return call_bitly_api(f"bitlinks/{domain}/{hash}/clicks/summary", params=params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/bitlinks/{bitlink}/countries", response_model=ClicksSummaryByCountry)
async def get_bitlink_countries(
    bitlink: str,
    current_username: str = Depends(get_current_user),
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
    unit: str = Query("day", enum=["minute", "hour", "day", "week", "month"]),
    units: int = Query(-1),
    size: Optional[int] = Query(50),
    unit_reference: Optional[str] = None,
):
    user = db.query(UserModel).filter(UserModel.username == current_username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db_link = (
        db.query(LinkModel)
        .filter(LinkModel.id == bitlink, LinkModel.owner == user)
        .first()
    )
    if not db_link:
        raise HTTPException(status_code=404, detail="Link not found")
    domain = db_link.bitlink.split("/")[2]
    hash = db_link.bitlink.split("/")[3]

    params = {
        "unit": unit,
        "units": units,
        "size": size,
        "unit_reference": unit_reference,
    }
    try:
        return call_bitly_api(f"bitlinks/{domain}/{hash}/countries", params=params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/shorten")
async def shorten_link(
    request: ShortenLinkRequest,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    username = get_current_user(token)
    user = db.query(UserModel).filter(UserModel.username == username).first()
    print(user)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    #  "long_url":"http://0.0.0.0:8000/api/track/?url=https://airforshare.com"
    params = request.dict()
    title = params.pop("title")
    long_url = params["long_url"]
    params["long_url"] = f'{REDIRECT_URL}/api/track?url={long_url}&user_id={user.id}'
    try:
        response = call_bitly_api("shorten", params=params, method="POST")
        bitlink = response['link']
        
        new_link = LinkModel(bitlink=bitlink, owner=user, expired=False, long_url = long_url, title = title)
        db.add(new_link)
        db.commit()
        db.refresh(new_link)

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/groups")
async def get_groups():
    try:
        return call_bitly_api("groups", params={})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/bitlinks")
async def get_user_links(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, "your-secret-key", algorithms=["HS256"])
        username = payload.get("username")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    db = SessionLocal()
    user = db.query(UserModel).filter(UserModel.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    links = db.query(LinkModel).filter(LinkModel.owner == user).all()
    return links


@app.get("/api/groups/{group_guid}/bitlinks")
async def get_bitlinks_by_group(
    group_guid: str,
    size: Optional[int] = Query(50),
    search_after: Optional[str] = None,
    query: Optional[str] = None,
    created_before: Optional[int] = None,
    created_after: Optional[int] = None,
    archived: Optional[str] = "off",
    deeplinks: Optional[str] = "both",
    domain_deeplinks: Optional[str] = "both",
    campaign_guid: Optional[str] = None,
    channel_guid: Optional[str] = None,
    custom_bitlink: Optional[str] = "both",
    tags: Optional[list] = None,
    launchpad_ids: Optional[list] = None,
    encoding_login: Optional[list] = None,
):
    params = {
        "size": size,
        "search_after": search_after,
        "query": query,
        "created_before": created_before,
        "created_after": created_after,
        "archived": archived,
        "deeplinks": deeplinks,
        "domain_deeplinks": domain_deeplinks,
        "campaign_guid": campaign_guid,
        "channel_guid": channel_guid,
        "custom_bitlink": custom_bitlink,
        "tags": tags,
        "launchpad_ids": launchpad_ids,
        "encoding_login": encoding_login,
    }
    try:
        return call_bitly_api(f"groups/{group_guid}/bitlinks", params=params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint to track IP and redirect
@app.get("/api/track")
async def track_and_redirect(url: str, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent")    
    logger.info(f"Client Public IP: {client_ip}")
    user_id = request.query_params.get("user_id")
    link = db.query(LinkModel).filter(LinkModel.long_url == url, LinkModel.user_id == user_id).first()
    
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    
    if link.expired:
        raise HTTPException(status_code=404, detail="Link has expired")
    
    time_threshold = datetime.now(timezone.utc) - timedelta(hours=24)
    existing_click = db.query(ClickModel).filter(
        ClickModel.ip == client_ip,
        ClickModel.user_agent == user_agent,
        ClickModel.timestamp >= time_threshold,
        ClickModel.link_id == link.id
    ).first()

    if not existing_click:
        link_id = link.id
        new_click = ClickModel(ip=client_ip, user_agent=user_agent, link_id=link_id)
        db.add(new_click)
        db.commit()
        db.refresh(new_click)

    return RedirectResponse(url=url)

@app.get("/api/bitlinks/{link_id}/clicks/unique")
async def get_unique_clicks(link_id: str, db: Session = Depends(get_db)): 
    unique_clicks = db.query(ClickModel).filter(ClickModel.link_id == link_id).all()
    
    unique_clicks_info = []
    for click in unique_clicks:
        ip_info = get_ip_info(click.ip)
        unique_clicks_info.append({
            "ip": click.ip,
            "timestamp": click.timestamp,
            "user_agent": click.user_agent,
            **ip_info
        })
    
    return {
        "unique_clicks": unique_clicks_info,
        "total_unique_clicks": len(unique_clicks_info)
    }


@app.get("/")
def index():
    return { "message": "Welcome to Bitly URL Shortener" }


if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=8000)
