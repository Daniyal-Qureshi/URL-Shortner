from fastapi import FastAPI, HTTPException, Query
from typing import Optional
from pydantic import BaseModel
import requests
import logging

app = FastAPI()

BITLY_API_BASE_URL = "https://api-ssl.bitly.com/v4"
BITLY_ACCESS_TOKEN = "f8d2f422017662bedfebc23a156e40e443be80e1"  

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ShortenLinkRequest(BaseModel):
    long_url: str
    domain: Optional[str] = "bit.ly"
    group_guid: Optional[str] = ""
    

def call_bitly_api(endpoint: str, params: dict = {}, method: str = "GET"):
    headers = {
        "Authorization": f"Bearer {BITLY_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    url = f"{BITLY_API_BASE_URL}/{endpoint}"
    print(url)
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
async def delete_bitlink(
    bitlink: str
):
    try:
        return call_bitly_api(f"bitlinks/{bitlink}", method="DELETE")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


@app.get("/api/bitlinks/{domain}/{hash}/clicks")
async def get_clicks(
    domain: str,
    hash: str,
    unit: str = Query("day", enum=["minute", "hour", "day", "week", "month"]),
    units: int = Query(-1),
    unit_reference: Optional[str] = None
):
    bitlink = f"{domain}/{hash}"
    params = {
        "unit": unit,
        "units": units,
        "unit_reference": unit_reference
    }
    try:
        return call_bitly_api(f"bitlinks/{bitlink}/clicks", params=params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/bitlinks/{domain}/{hash}/countries")
async def get_bitlink_countries(
    domain: str,
    hash: str,
    unit: str = Query("day", enum=["minute", "hour", "day", "week", "month"]),
    units: int = Query(-1),
    size: Optional[int] = Query(50)
):
    bitlink = f"{domain}/{hash}"
    params = {
        "unit": unit,
        "units": units,
        "size": size
    }
    try:
        return call_bitly_api(f"bitlinks/{bitlink}/countries", params=params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/shorten")
async def shorten_link(request: ShortenLinkRequest):
    params = request.dict()
   
    try:
        return call_bitly_api("shorten", params=params, method="POST")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/groups")
async def get_groups():
    try:
        return call_bitly_api("groups", params={})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
