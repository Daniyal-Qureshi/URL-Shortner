from fastapi import FastAPI, HTTPException, Depends, status, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Optional, List
import requests
import logging
from pydantic import BaseModel
from requests.exceptions import HTTPError, JSONDecodeError
from sqlalchemy.orm import Session

# Database setup
from models import Base, User as UserModel, Link as LinkModel
from Schemas import User as UserSchema, Link as LinkSchema

app = FastAPI()

# Configure logging
logger = logging.getLogger('app')
logger.setLevel(logging.DEBUG)

fh = logging.FileHandler("QED.log")
fh.setLevel(logging.ERROR)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)

logger.addHandler(fh)
logger.addHandler(ch)


DATABASE_URL = "sqlite:///./test4.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

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
async def authenticate(formdata: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    logger.info("Authenticating user")
    logger.debug(f"Username: {formdata.username}")
    username = formdata.username
    password = formdata.password
    url = 'https://flex-api.sharetribe.com/v1/auth/token'
    payload = {
        'client_id': 'dc31b12f-8294-4e24-b027-24ce590ffd16',
        'grant_type': 'password',
        'username': username,
        'password': password,
        'scope': 'user'
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
        'Accept': 'application/json'
    }
    # response = requests.post(url, data=payload, headers=headers)

    # return {username, password}
    try:
        response = requests.post(url, data=payload, headers=headers)
        response.raise_for_status()
        external_api_response = response.json()
        print(external_api_response)

        #if the user exist in the database then return a new jwt token
        user = db.query(UserModel).filter(UserModel.username == username).first()
        if user:
            token_payload = {"username": username}
            token = jwt.encode(token_payload, SECRET_KEY, algorithm=ALGORITHM)
            return {"id":user.id,"username":username,"access_token": token, "token_type": "bearer"}
        else:
            user = UserModel(username=username, external_api_token=external_api_response["access_token"])
            db.add(user)
            db.commit()
            token_payload = {"username": username}
            token = jwt.encode(token_payload, SECRET_KEY, algorithm=ALGORITHM)
            return {"id":user.id,"username":username,"access_token": token, "token_type": "bearer"}

    except HTTPError as http_err:
        raise HTTPException(status_code=http_err.response.status_code, detail=http_err.response.text)
    except JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid JSON response from server")
    except KeyError:
        raise HTTPException(status_code=500, detail="Access token not found in external API response")
    
def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("username")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
        return username
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

@app.get("/api/users/me", response_model=UserSchema)
async def read_users_me(current_username: str = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.username == current_username).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

from sqlalchemy.orm import joinedload

@app.get("/api/users/{user_id}/links", response_model=List[LinkSchema])
async def get_user_links(user_id: int, current_username: str = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.username != current_username:
        raise HTTPException(status_code=403, detail="Not authorized to view this user's links")
    links = db.query(LinkModel).options(joinedload(LinkModel.owner)).filter(LinkModel.owner.has(id=user_id)).all()
    return links

class ShortenLinkRequest(BaseModel):
    long_url: str
    domain: Optional[str] = "bit.ly"
    group_guid: Optional[str] = ""

BITLY_API_BASE_URL = "https://api-ssl.bitly.com/v4"
BITLY_ACCESS_TOKEN = "f8d2f422017662bedfebc23a156e40e443be80e1"  


def call_bitly_api(endpoint: str, params: dict = {}, method: str = "GET"):
    headers = {
        "Authorization": f"Bearer {BITLY_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    url = f"{BITLY_API_BASE_URL}/{endpoint}"
    if method == "GET":
        response = requests.get(url, headers=headers, params=params)
    elif method == "POST":
        response = requests.post(url, headers=headers, json=params)
    elif method == "DELETE":
        response = requests.delete(url, headers=headers, json=params)
    else:
        raise ValueError("Unsupported HTTP method")

    response.raise_for_status()
    return response.json()

@app.delete("/api/bitlinks/{bitlink}")
async def delete_bitlink(bitlink: str):
    try:
        return call_bitly_api(f"bitlinks/{bitlink}", method="DELETE")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/bitlinks/{bitlink}/clicks")
async def get_clicks(
    bitlink: str,
    current_username: str = Depends(get_current_user),
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
    unit: str = Query("day", enum=["minute", "hour", "day", "week", "month"]),
    units: int = Query(-1),
    unit_reference: Optional[str] = None
):
    user = db.query(UserModel).filter(UserModel.username == current_username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db_link = db.query(LinkModel).filter(LinkModel.id == bitlink, LinkModel.owner == user).first()
    if not db_link:
        raise HTTPException(status_code=404, detail="Link not found")
    # extract domain and hash from bitlink
    domain = db_link.bitlink.split("/")[2]
    hash = db_link.bitlink.split("/")[3]
    params = {
        "unit": unit,
        "units": units,
        "unit_reference": unit_reference
    }
    try:
        return call_bitly_api(f"bitlinks/{domain}/{hash}/clicks", params=params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/bitlinks/{bitlink}/countries")
async def get_bitlink_countries(
    bitlink: str,
    current_username: str = Depends(get_current_user),
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
    unit: str = Query("day", enum=["minute", "hour", "day", "week", "month"]),
    units: int = Query(-1),
    size: Optional[int] = Query(50)
):
    user = db.query(UserModel).filter(UserModel.username == current_username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db_link = db.query(LinkModel).filter(LinkModel.id == bitlink, LinkModel.owner == user).first()
    if not db_link:
        raise HTTPException(status_code=404, detail="Link not found")
    domain = db_link.bitlink.split("/")[2]
    hash = db_link.bitlink.split("/")[3]

    params = {
        "unit": unit,
        "units": units,
        "size": size
    }
    try:
        return call_bitly_api(f"bitlinks/{domain}/{hash}/countries", params=params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/api/shorten")
async def shorten_link(request: ShortenLinkRequest, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    username = get_current_user(token)
    user = db.query(UserModel).filter(UserModel.username == username).first()
    print(user)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    params = request.dict()
    try:
        response = call_bitly_api("shorten", params=params, method="POST")
        bitlink = response['link']

        # Store the shortened link in the database with the user as the owner
        new_link = LinkModel(bitlink=bitlink, owner=user)
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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

    db = SessionLocal()
    user = db.query(UserModel).filter(UserModel.username == username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

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
    encoding_login: Optional[list] = None
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
        "encoding_login": encoding_login
    }
    try:
        return call_bitly_api(f"groups/{group_guid}/bitlinks", params=params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)