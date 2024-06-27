import pytest
import datetime
from app.main import app 
from httpx import ASGITransport, AsyncClient

@pytest.mark.asyncio
async def test_build_user_charts():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac: # type: ignore
        response = await ac.post("/api/astrology/user/charts", json={
            "latitude": 40.7128,
            "longitude": -74.0060,
            "birth_datetime": "1990-01-01T12:00:00"
        })
        assert response.status_code == 200
        data = response.json()
        assert "sun" in data
        assert "moon" in data
        assert "ascendant" in data

@pytest.mark.asyncio
async def test_get_zodiac_description():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac: # type: ignore
        response = await ac.post("/api/astrology/user/zodiac/description", json={
            "celestial_body": "sun",
            "zodiac_sign": "aries",
            "english_house_number": "first"
        })
        assert response.status_code == 200
        data = response.json()
        assert "general_body_description" in data
        assert "general_body_themes" in data
        assert "zodiac_traits" in data
        assert "zodiac_description_for_body" in data
        assert "body_in_house" in data

@pytest.mark.asyncio
async def test_compare_two_charts():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac: # type: ignore
        response = await ac.post("/api/astrology/compare", json={
            "person_1": {
                "latitude": 40.7128,
                "longitude": -74.0060,
                "birth_datetime": "1990-01-01T12:00:00"
            },
            "person_2": {
                "latitude": 34.0522,
                "longitude": -118.2437,
                "birth_datetime": "1992-02-02T14:00:00"
            }
        })
        assert response.status_code == 200
        data = response.json()
        assert "all_compared" in data
        assert "overall_score" in data
        assert "sun" in data["all_compared"]
        assert "moon" in data["all_compared"]
        assert "ascendant" in data["all_compared"]
        print(f"Your overall astrological compatibility score is: {data['all_compared']}%")

# Test for PlanetaryData Singleton
def test_planetary_data_singleton():
    from app.astrology.utils import PlanetaryData
    instance1 = PlanetaryData()
    instance2 = PlanetaryData()
    assert instance1 is instance2

# Test for AstrologyDescriptions Class
def test_astrology_descriptions():
    from app.astrology.utils import AstrologyDescriptions
    descriptions = AstrologyDescriptions()
    result = descriptions.description("sun", "aries", "first")
    assert "general_body_description" in result
    assert "general_body_themes" in result
    assert "zodiac_traits" in result
    assert "zodiac_description_for_body" in result
    assert "body_in_house" in result

# Test for Astrology Class
def test_astrology():
    from app.astrology.utils import Astrology
    birth_datetime = datetime.datetime(1990, 1, 1, 12, 0, 0)
    astrology = Astrology(latitude=40.7128, longitude=-74.0060, birth_datetime=birth_datetime)
    chart = astrology.compute_houses_and_ascendant()
    assert "sun" in chart.model_dump()
    assert "moon" in chart.model_dump()
    assert "ascendant" in chart.model_dump()