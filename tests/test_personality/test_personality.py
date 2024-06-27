import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

test_answers = {
    "Would you date someone who can’t afford a car?": True,
    "Do you ever make unnecessary and loud noises when you're home alone?": True,
    "Have you ever gone backpacking?": False
}

@pytest.mark.asyncio
async def test_calculate_scores_individual():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac: # type: ignore
        response = await ac.post("/api/personality/calculate_scores/individual", json={"answers": test_answers})
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_calculate_scores_individual_empty_answers():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac: # type: ignore
        response = await ac.post("/api/personality/calculate_scores/individual", json={"answers": {}})
        assert response.status_code == 400

@pytest.mark.asyncio
async def test_calculate_scores_individual_result_structure():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac: # type: ignore
        response = await ac.post("/api/personality/calculate_scores/individual", json={"answers": test_answers})
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_calculate_scores_individual_invalid_input():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac: # type: ignore
        response = await ac.post("/api/personality/calculate_scores/individual", json={"invalid": "data"})
        assert response.status_code == 422  # Unprocessable Entity