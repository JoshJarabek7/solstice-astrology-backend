from fastapi import FastAPI
from app.astrology.api import router as astrology_router
from app.personality.api import router as personality_router
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



app = FastAPI()

@app.get("/check")
async def check_health():
    return {"success": True}

    
app.include_router(astrology_router)
app.include_router(personality_router)