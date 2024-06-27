from pydantic import BaseModel, Field
from typing import Literal, List
from enum import Enum
import datetime

# Define constants
SIGNS = Literal['aries', 'taurus', 'gemini', 'cancer', 'leo', 'virgo', 'libra', 'scorpio', 'sagittarius', 'capricorn', 'aquarius', 'pisces']

# Define Pydantic models for data validation
class AstrologyIndividual(BaseModel):
    """Represents an individual's zodiac sign and house number."""
    zodiac_sign: SIGNS
    house_number: int

class AstrologyChart(BaseModel):
    """Represents an astrology chart with various celestial bodies."""
    sun: AstrologyIndividual
    moon: AstrologyIndividual
    ascendant: SIGNS
    mercury: AstrologyIndividual
    venus: AstrologyIndividual
    mars: AstrologyIndividual
    jupiter: AstrologyIndividual
    saturn: AstrologyIndividual
    uranus: AstrologyIndividual
    neptune: AstrologyIndividual
    pluto: AstrologyIndividual

class ComparedSign(BaseModel):
    """Represents the compatibility score and description between two signs."""
    description: str = ""
    compatibility_score: float = -1.0

class EachComparedSign(BaseModel):
    """Represents the compatibility data for each zodiac sign."""
    aries: ComparedSign = ComparedSign()
    taurus: ComparedSign = ComparedSign()
    gemini: ComparedSign = ComparedSign()
    cancer: ComparedSign = ComparedSign()
    leo: ComparedSign = ComparedSign()
    virgo: ComparedSign = ComparedSign()
    libra: ComparedSign = ComparedSign()
    scorpio: ComparedSign = ComparedSign()
    sagittarius: ComparedSign = ComparedSign()
    capricorn: ComparedSign = ComparedSign()
    aquarius: ComparedSign = ComparedSign()
    pisces: ComparedSign = ComparedSign()

class SignAttributes(BaseModel):
    """Represents the traits, description, and compatibility of a zodiac sign."""
    traits: List[str] = Field(default_factory=list)
    description: str = ""
    compatibility: EachComparedSign = EachComparedSign()

class AllSigns(BaseModel):
    """Represents the attributes of all zodiac signs."""
    aries: SignAttributes = SignAttributes()
    taurus: SignAttributes = SignAttributes()
    gemini: SignAttributes = SignAttributes()
    cancer: SignAttributes = SignAttributes()
    leo: SignAttributes = SignAttributes()
    virgo: SignAttributes = SignAttributes()
    libra: SignAttributes = SignAttributes()
    scorpio: SignAttributes = SignAttributes()
    sagittarius: SignAttributes = SignAttributes()
    capricorn: SignAttributes = SignAttributes()
    aquarius: SignAttributes = SignAttributes()
    pisces: SignAttributes = SignAttributes()

class AllHouses(BaseModel):
    """Represents the description of all houses."""
    general: str = ""
    first: str = ""
    second: str = ""
    third: str = ""
    fourth: str = ""
    fifth: str = ""
    sixth: str = ""
    seventh: str = ""
    eighth: str = ""
    ninth: str = ""
    tenth: str = ""
    eleventh: str = ""
    twelfth: str = ""

class IndividualPlanet(BaseModel):
    """Represents the description, themes, signs, and houses of an individual planet."""
    description: str = ""
    themes: List[str] = Field(default_factory=list)
    signs: AllSigns = AllSigns()
    houses: AllHouses = AllHouses()

class AllPlanets(BaseModel):
    """Represents the attributes of all planets."""
    sun: IndividualPlanet = IndividualPlanet()
    moon: IndividualPlanet = IndividualPlanet()
    ascendant: IndividualPlanet = IndividualPlanet()
    mercury: IndividualPlanet = IndividualPlanet()
    venus: IndividualPlanet = IndividualPlanet()
    mars: IndividualPlanet = IndividualPlanet()
    jupiter: IndividualPlanet = IndividualPlanet()
    saturn: IndividualPlanet = IndividualPlanet()
    uranus: IndividualPlanet = IndividualPlanet()
    neptune: IndividualPlanet = IndividualPlanet()
    pluto: IndividualPlanet = IndividualPlanet()

class AllCompared(BaseModel):
    """Represents the comparison between two astrology charts for all planets."""
    sun: ComparedSign
    moon: ComparedSign
    ascendant: ComparedSign
    mercury: ComparedSign
    venus: ComparedSign
    mars: ComparedSign
    jupiter: ComparedSign
    saturn: ComparedSign
    uranus: ComparedSign
    neptune: ComparedSign
    pluto: ComparedSign

class AllComparedWithOverallScore(BaseModel):
    """Represents the overall comparison score and individual comparisons for each planet."""
    all_compared: AllCompared
    overall_score: float # On a scale of 0-100

# Define Enums for Zodiac and Planets
class Zodiac(Enum):
    """Enum for zodiac signs."""
    ARIES = "aries"
    TAURUS = "taurus"
    GEMINI = "gemini"
    CANCER = "cancer"
    LEO = "leo"
    VIRGO = "virgo"
    LIBRA = "libra"
    SCORPIO = "scorpio"
    SAGITTARIUS = "sagittarius"
    CAPRICORN = "capricorn"
    AQUARIUS = "aquarius"
    PISCES = "pisces"

class Planet(Enum):
    """Enum for planets."""
    SUN = "sun"
    MOON = "moon"
    MERCURY = "mercury"
    VENUS = "venus"
    MARS = "mars"
    JUPITER = "jupiter"
    SATURN = "saturn"
    URANUS = "uranus"
    NEPTUNE = "neptune"
    PLUTO = "pluto"
    ASCENDANT = "ascendant"

class House(Enum):
    """Enum for houses."""
    FIRST = "first"
    SECOND = "second"
    THIRD = "third"
    FOURTH = "fourth"
    FIFTH = "fifth"
    SIXTH = "sixth"
    SEVENTH = "seventh"
    EIGHTH = "eighth"
    NINTH = "ninth"
    TENTH = "tenth"
    ELEVENTH = "eleventh"
    TWELFTH = "twelfth"
    GENERAL = "general"

class InboundAstrologyChartSchema(BaseModel):
    """Schema for incoming astrology chart data."""
    latitude: float
    longitude: float
    birth_datetime: datetime.datetime

class InboundAstrologyDescriptionSchema(BaseModel):
    """Schema for incoming astrology description request."""
    celestial_body: str
    zodiac_sign: str
    english_house_number: str

class OutboundAstrologyDescriptionSchema(BaseModel):
    """Schema for outgoing astrology description response."""
    general_body_description: str
    general_body_themes: List[str]
    zodiac_traits: List[str]
    zodiac_description_for_body: str
    body_in_house: str

class InboundCompareTwoCharts(BaseModel):
    """Schema for incoming request to compare two astrology charts."""
    person_1: InboundAstrologyChartSchema
    person_2: InboundAstrologyChartSchema

