from pydantic import BaseModel
from typing import List
from datetime import datetime


class Link(BaseModel):
    id: int
    bitlink: str
    user_id: int
    created_at: datetime
    long_url: str
    title: str

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


class ShareTribeUserAttributesProfile(BaseModel):
    displayName: str
    abbreviatedName: str

class ShareTribeUserAttributes(BaseModel):
    email: str
    profile: ShareTribeUserAttributesProfile

class ShareTribeUser(BaseModel):
    id: str
    type: str
    attributes: ShareTribeUserAttributes

    class Config:
        from_attributes = True

class ShareTribeIncludedImageAttributesVariant(BaseModel):
    url: str
    width: int
    height: int

class ShareTribeIncludedImageAttributes(BaseModel):
    variants: dict[str, ShareTribeIncludedImageAttributesVariant]

class ShareTribeIncludedImage(BaseModel):
    id: str
    type: str
    attributes: ShareTribeIncludedImageAttributes

    class Config:
        from_attributes = True

class ShareTribeUserResponse(BaseModel):
    data: ShareTribeUser
    included: List[ShareTribeIncludedImage] | None = None

    class Config:
        from_attributes = True
