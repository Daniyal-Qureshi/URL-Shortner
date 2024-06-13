from pydantic import BaseModel
from typing import List
from datetime import datetime


class Link(BaseModel):
    id: int
    bitlink: str
    user_id: int
    created_at: datetime
    long_url: str

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
