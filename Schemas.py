from pydantic import BaseModel
from typing import List

class Link(BaseModel):
    id: int
    bitlink: str
    user_id: int
    

    class Config:
        from_attributes = True

class User(BaseModel):
    id: int
    username: str
    links: List[Link] = []
    external_api_token: str

    class Config:
        from_attributes = True
