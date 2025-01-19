from pydantic import BaseModel
from typing import List
from datetime import datetime
from typing import List, Optional
from datetime import datetime

class Click(BaseModel):
    id: int
    ip: str
    timestamp: datetime
    user_agent: str
    link_id: int
    
    class Config:
        from_attributes = True

class Link(BaseModel):
    id: int
    bitlink: str
    user_id: int
    created_at: datetime
    long_url: str
    short_url: str
    title: str

    expired: bool
    
    class Config:
        from_attributes = True


class User(BaseModel):
    id: int
    username: str
    links: List[Link] = []
    external_api_token: str

    class Config:
        from_attributes = True


class TotalClicksSummary(BaseModel):
    unit_reference: datetime
    total_clicks: int
    units: int
    unit: str

    class Config:
        from_attributes = True


class ClickLink(BaseModel):
    date: datetime
    clicks: int

    class Config:
        from_attributes = True


class ClicksSummary(BaseModel):
    unit_reference: datetime
    link_clicks: List[ClickLink]
    units: int
    unit: str

    class Config:
        from_attributes = True

class ClicksSummaryByCountryMetrics(BaseModel):
    clicks: int
    value: str

    class Config:
        from_attributes = True

class ClicksSummaryByCountry(BaseModel):
    unit_reference: datetime
    metrics: List[ClicksSummaryByCountryMetrics]
    units: int
    unit: str
    facet: str

    class Config:
        from_attributes = True



class IPInfo(BaseModel):
    id: int
    ip: str
    city: str
    region: str
    country: str
    loc: str
    org: str
    postal: str
    timezone: str
    click_id: int


class ShortenLinkResponse(BaseModel):
    link: str
    title: str
    long_url: str
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class UserBody(BaseModel):
    username: str
    password: str
    
    class Config:
        form_attributes = True  

class Token(BaseModel):
    access_token: str
    token_type: str
    
class ShortenLinkRequest(BaseModel):
    title: str
    long_url: str
    custom_back_half: Optional[str] = None