# main.py

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from routers.controllers import router
from fastapi.middleware.cors import CORSMiddleware

from models.models import Base
import uvicorn
from config.config import engine

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)


app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

