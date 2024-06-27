from fastapi import APIRouter
from .schemas import AstrologyChart, InboundAstrologyChartSchema, OutboundAstrologyDescriptionSchema, InboundAstrologyDescriptionSchema, InboundCompareTwoCharts, AllComparedWithOverallScore
from .utils import Astrology, AstrologyDescriptions, ComparisonHandler
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder


router = APIRouter(prefix="/api/astrology")

@router.post("/user/charts", response_model=AstrologyChart)
async def build_user_charts(request: InboundAstrologyChartSchema):
    """Builds the astrology chart for a user based on their birth details.

    Returns:
        AstrologyChart: The generated astrology chart.
    """
    try:
        astrology = Astrology(latitude=request.latitude, longitude=request.longitude, birth_datetime=request.birth_datetime)
        chart = astrology.compute_houses_and_ascendant()
        print(chart)
        return jsonable_encoder(chart)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/user/zodiac/description", response_model=OutboundAstrologyDescriptionSchema)
async def get_zodiac_description(request: InboundAstrologyDescriptionSchema):
    """Gets the zodiac description for a celestial body in a specific sign and house.

    Args:
        request (InboundAstrologyDescriptionSchema): The request containing the celestial body, zodiac sign, and house number.

    Returns:
        OutboundAstrologyDescriptionSchema: The zodiac description.
    """
    try:
        astrology_descriptions = AstrologyDescriptions()
        desc = astrology_descriptions.description(request.celestial_body, request.zodiac_sign, request.english_house_number)
        return jsonable_encoder(desc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/compare", response_model=AllComparedWithOverallScore)
async def compare_two_charts(request: InboundCompareTwoCharts):
    """Compares two astrology charts and returns the comparison result.

    Args:
        request (InboundCompareTwoCharts): The request containing two astrology charts to compare.

    Returns:
        AllComparedWithOverallScore: The comparison result with an overall score.
    """
    try:
        compare = ComparisonHandler(request.person_1, request.person_2)
        outbound = compare.compare()
        return outbound
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))