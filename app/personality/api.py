from fastapi import APIRouter, HTTPException
from .schemas import UserAnswers
import logging
from .utils import ScoreKeeper

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/personality")

@router.post("/calculate_scores/individual")
async def calculate_scores(user_answers: UserAnswers):
    try:
        logger.info(f"Received answers: {user_answers.answers}")
        if not user_answers.answers:
            raise ValueError("Answers cannot be empty")
        sk = ScoreKeeper()
        normalized_scores = sk.calculate_individual(user_answers.answers, sk.instance.weights)
        logger.info(f"Calculation result: {normalized_scores}")
        return {"traits_scores": normalized_scores}
    except ValueError as ve:
        logger.error(f"ValueError: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))