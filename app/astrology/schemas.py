from datetime import datetime

from pydantic import BaseModel


class AstrologyCompatibilityDetails(BaseModel):
    """Represents the compatibility details for an astrology profile."""

    description: str
    score: float


class AstrologyCompatibility(BaseModel):
    """Represents the compatibility of two astrology profiles."""

    aries: AstrologyCompatibilityDetails
    taurus: AstrologyCompatibilityDetails
    gemini: AstrologyCompatibilityDetails
    cancer: AstrologyCompatibilityDetails
    leo: AstrologyCompatibilityDetails
    virgo: AstrologyCompatibilityDetails
    libra: AstrologyCompatibilityDetails
    scorpio: AstrologyCompatibilityDetails
    sagittarius: AstrologyCompatibilityDetails
    capricorn: AstrologyCompatibilityDetails
    aquarius: AstrologyCompatibilityDetails
    pisces: AstrologyCompatibilityDetails


class AstrologySign(BaseModel):
    """Represents the details of a single sign in the JSON file."""

    traits: list[str]
    description: str
    compatibility: AstrologyCompatibility


class AstrologySigns(BaseModel):
    """Represents the details of all signs in the JSON file."""

    aries: AstrologySign
    taurus: AstrologySign
    gemini: AstrologySign
    cancer: AstrologySign
    leo: AstrologySign
    virgo: AstrologySign
    libra: AstrologySign
    scorpio: AstrologySign
    sagittarius: AstrologySign
    capricorn: AstrologySign
    aquarius: AstrologySign
    pisces: AstrologySign


class AstrologyBody(BaseModel):
    """Represents the details of a single astrology body in the JSON file."""

    description: str
    themes: list[str]
    signs: AstrologySigns


class AstrologyData(BaseModel):
    """Represents the details of all astrology bodies in the JSON file."""

    sun: AstrologyBody
    moon: AstrologyBody
    ascendant: AstrologyBody
    mercury: AstrologyBody
    venus: AstrologyBody
    mars: AstrologyBody
    jupiter: AstrologyBody
    saturn: AstrologyBody
    uranus: AstrologyBody
    neptune: AstrologyBody
    pluto: AstrologyBody


class AstrologyChartCreationRequest(BaseModel):
    """Request model for creating an astrology chart."""

    birth_datetime: datetime
    latitude: float
    longitude: float


class UserAstrology(BaseModel):
    """Represents a user's astrology (simple)."""

    birth_datetime_utc: datetime | None = None
    birth_location: tuple[float, float] | None = None
    sun: str
    moon: str
    ascendant: str
    mercury: str
    venus: str
    mars: str
    jupiter: str
    saturn: str
    uranus: str
    neptune: str
    pluto: str


class AstrologyBodyDetails(BaseModel):
    """Represents the details of an as astrology body."""

    body_description: str
    body_themes: list[str]
    sign: str
    sign_description: str
    sign_traits: list[str]


class AstrologyDetailsSingleUser(BaseModel):
    """Represents the details of an astrology profile for a single user."""

    sun: AstrologyBodyDetails
    moon: AstrologyBodyDetails
    ascendant: AstrologyBodyDetails
    mercury: AstrologyBodyDetails
    venus: AstrologyBodyDetails
    mars: AstrologyBodyDetails
    jupiter: AstrologyBodyDetails
    saturn: AstrologyBodyDetails
    uranus: AstrologyBodyDetails
    neptune: AstrologyBodyDetails
    pluto: AstrologyBodyDetails


class AstrologyDetailsComparedDetails(BaseModel):
    """Represents the details of a comparison between two astrology profiles for a single body."""

    body_description: str
    body_themes: list[str]
    requesting_user_sign: str
    target_user_sign: str
    description: str
    score: float


class AstrologyDetailsCompared(BaseModel):
    """Represents the overall comparison between two astrology profiles."""

    sun: AstrologyDetailsComparedDetails
    moon: AstrologyDetailsComparedDetails
    ascendant: AstrologyDetailsComparedDetails
    mercury: AstrologyDetailsComparedDetails
    venus: AstrologyDetailsComparedDetails
    mars: AstrologyDetailsComparedDetails
    jupiter: AstrologyDetailsComparedDetails
    saturn: AstrologyDetailsComparedDetails
    uranus: AstrologyDetailsComparedDetails
    neptune: AstrologyDetailsComparedDetails
    pluto: AstrologyDetailsComparedDetails
    total_score: float
