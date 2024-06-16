from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import datetime

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
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    title = Column(String, nullable=False)
    long_url = Column(String, nullable=False)
    owner = relationship("User", back_populates="links")
