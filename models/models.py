from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    external_api_token = Column(String, index=True, unique=True)
    links = relationship("Link", back_populates="owner")


class Link(Base):
    __tablename__ = "links"
    id = Column(Integer, primary_key=True, index=True)
    bitlink = Column(String, index=True, nullable=False)
    long_url = Column(String, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    title = Column(String, nullable=False)
    short_url = Column(String, index=True, unique=True)
    owner = relationship("User", back_populates="links")
    expired = Column(Boolean, default=False)

class Click(Base):
    __tablename__ = 'clicks'
    id = Column(Integer, primary_key=True, index=True)
    ip = Column(String)
    # please don't use datetime.utcnow it is not working
    timestamp = Column(DateTime, default=datetime.now) 
    user_agent = Column(String)
    link_id = Column(Integer, ForeignKey('links.id'))


class IPInfo(Base):
    __tablename__ = 'ip_info'
    id = Column(Integer, primary_key=True, index=True)
    ip = Column(String)
    city = Column(String)
    region = Column(String)
    country = Column(String)
    loc = Column(String)
    org = Column(String)
    postal = Column(String)
    timezone = Column(String)
    click_id = Column(Integer, ForeignKey('clicks.id'), unique=True)
