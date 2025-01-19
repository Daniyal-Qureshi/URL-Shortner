from dotenv import load_dotenv
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer

from config.dependencies import get_link_service
from middlewares.link_validation import validate_link_middleware
from middlewares.user_validation import validate_user_middleware
from services.link_service import LinkService
load_dotenv()

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from routers import link, auth, click
from fastapi.middleware.cors import CORSMiddleware
from models.models import Base
import uvicorn
from config.config import (
    engine
)

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

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(link.router, prefix="/link", tags=["link"])
app.include_router(click.router, prefix="/click", tags=["click"])

@app.get("/{short_url}")
async def redirect_to_long_url(
    request: Request,
    background_tasks: BackgroundTasks,
    link = Depends(validate_link_middleware),  
    link_service: LinkService = Depends(get_link_service),
):
    try:
        link_service.redirect_to_url(link, request, background_tasks)
        return RedirectResponse(url=link.long_url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

