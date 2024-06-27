from .schemas import AllPlanets, IndividualPlanet, SignAttributes, AstrologyChart, AllHouses, InboundAstrologyChartSchema, InboundAstrologyDescriptionSchema, InboundCompareTwoCharts, IndividualPlanet, OutboundAstrologyDescriptionSchema, AllCompared, AllComparedWithOverallScore, AllSigns, Planet, ComparedSign, SIGNS, AstrologyIndividual
import swisseph as swe
import pytz
from typing import Dict, Tuple, List, Union
from timezonefinder import TimezoneFinder
import datetime
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Singleton class to load and hold the planetary data
class PlanetaryData:
    """Singleton class to load and hold the planetary data.
    
    Attributes:
        _instance (PlanetaryData): The singleton instance.
        _data (AllPlanets): The planetary data loaded from the JSON file.
    """
    _instance = None
    _data: AllPlanets

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PlanetaryData, cls).__new__(cls)
            cls._data = cls._load_planetary_json()
        return cls._instance

    @staticmethod
    def _load_planetary_json() -> AllPlanets:
        """Loads planetary data from the JSON file."""
        with open("zodiac_data.json", "r") as f:
            contents = f.read()
        return AllPlanets.model_validate_json(contents)

    @property
    def data(self) -> AllPlanets:
        """Returns the planetary data."""
        return self._data


# AstrologyDescriptions class
class AstrologyDescriptions:
    """Class to get astrology descriptions based on celestial body, zodiac sign, and house number.
    
    Attributes:
        astrology_data (AllPlanets): The planetary data.
    """
    def __init__(self):
        self.astrology_data = PlanetaryData().data

    def description(self, celestial_body: str, zodiac_sign: str, english_house_number: str) -> Dict[str, Union[str, List[str]]]:
        """Gets the astrology description for a given celestial body, zodiac sign, and house number.

        Args:
            celestial_body (str): The celestial body.
            zodiac_sign (str): The zodiac sign.
            english_house_number (str): The house number.

        Returns:
            Dict[str, Union[str, List[str]]]: The astrology description.
        """
        body: IndividualPlanet = getattr(self.astrology_data, celestial_body)
        general_body_desc = body.description
        general_body_themes = body.themes
        body_signs = body.signs
        body_plus_zod: SignAttributes = getattr(body_signs, zodiac_sign)
        zod_traits = body_plus_zod.traits
        zod_description = body_plus_zod.description
        body_houses: AllHouses = getattr(body, "houses")
        body_plus_house: str = getattr(body_houses, english_house_number)

        return {
            "general_body_description": general_body_desc,
            "general_body_themes": general_body_themes,
            "zodiac_traits": zod_traits,
            "zodiac_description_for_body": zod_description,
            "body_in_house": body_plus_house
        }

# Astrology class
class Astrology:
    """Class to handle astrology chart calculations.

    Attributes:
        SIGNS (List[str]): List of zodiac signs.
        BODIES (Dict[str, int]): Mapping of celestial body names to Swiss Ephemeris IDs.
        HOUSE_SYSTEMS (Dict[str, bytes]): Mapping of house system names to their respective codes.
    """
    SIGNS = [
        'Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
    ]
    
    BODIES = {
        'Sun': swe.SUN,
        'Moon': swe.MOON,
        'Mercury': swe.MERCURY,
        'Venus': swe.VENUS,
        'Mars': swe.MARS,
        'Jupiter': swe.JUPITER,
        'Saturn': swe.SATURN,
        'Uranus': swe.URANUS,
        'Neptune': swe.NEPTUNE,
        'Pluto': swe.PLUTO,
    }

    HOUSE_SYSTEMS = {
        'Porphyry': b"O",
        'Placidus': b"P",
        'Koch': b"K",
        'Regiomontanus': b"R",
        'Campanus': b"C",
        'Equal': b"E",
        'Vehlow': b"V",
        'Whole Sign': b"W",
    }

    def __init__(self, latitude: float, longitude: float, birth_datetime: datetime.datetime, tz: Union[pytz.BaseTzInfo, None] = None):
        """Initializes the Astrology class with the given latitude, longitude, birth datetime, and timezone.

        Args:
            latitude (float): The latitude.
            longitude (float): The longitude.
            birth_datetime (datetime.datetime): The birth datetime.
            tz (Union[pytz.BaseTzInfo, None], optional): The timezone. Defaults to None.
        """
        self.latitude = latitude
        self.longitude = longitude
        self.birth_datetime = birth_datetime
        self.tz = tz or self._find_timezone()
        self.birth_datetime_utc = self._convert_to_utc()
        self.julian_day = self._calculate_julian_day()
        
        self.positions: Dict[str, float] = {}
        self.body_houses: Dict[str, int] = {}
        self.body_signs: Dict[str, str] = {}

    def _find_timezone(self) -> pytz.BaseTzInfo:
        """Finds the timezone for the given latitude and longitude."""
        tf = TimezoneFinder()
        timezone_str = tf.timezone_at(lng=self.longitude, lat=self.latitude)
        if timezone_str:
            return pytz.timezone(timezone_str)
        raise ValueError("Timezone could not be determined.")

    def _convert_to_utc(self) -> datetime.datetime:
        """Converts the birth datetime to UTC."""
        return self.birth_datetime.astimezone(pytz.utc)

    def _calculate_julian_day(self) -> float:
        """Calculates the Julian day for the birth datetime."""
        return swe.julday(
            self.birth_datetime_utc.year,
            self.birth_datetime_utc.month,
            self.birth_datetime_utc.day,
            self.birth_datetime_utc.hour + self.birth_datetime_utc.minute / 60.0 + self.birth_datetime_utc.second / 3600.0
        )
    def compute_houses_and_ascendant(self, house_system: str = 'Porphyry') -> AstrologyChart:
        """Computes the houses and ascendant for the astrology chart.

        Args:
            house_system (str, optional): The house system to use. Defaults to 'Porphyry'.

        Returns:
            AstrologyChart: The computed astrology chart.
        """
        houses, ascendant = self._calculate_houses_and_ascendant("Porphyry")
        self._calculate_body_positions()
        self._assign_houses_to_bodies(houses)
        self._assign_signs_to_bodies()
        
        ascendant_sign = self._get_sign_for_position(ascendant)
        return self._create_astrology_chart(str(ascendant_sign).lower())

    def _create_astrology_chart(self, ascendant: str) -> AstrologyChart:
        """Creates the astrology chart."""
        chart_data = {
            "sun": None,
            "moon": None,
            "ascendant": ascendant,
            "mercury": None,
            "venus": None,
            "mars": None,
            "jupiter": None,
            "saturn": None,
            "uranus": None,
            "neptune": None,
            "pluto": None
        }

        for body_name in self.BODIES.keys():

            chart_data[body_name.lower()] = self._create_astrology_individual(
                self.body_signs[body_name].lower(),
                self.body_houses[body_name]
            )

        return AstrologyChart(**chart_data)

    def _calculate_houses_and_ascendant(self, house_system: str) -> Tuple[List[float], float]:
        """Calculates the houses and ascendant using the specified house system."""
        hsys = self.HOUSE_SYSTEMS.get(house_system, b"O")  # Default to Porphyry
        flags = swe.FLG_SWIEPH + swe.FLG_SPEED
        try:
            result = swe.houses(self.julian_day, self.latitude, self.longitude, hsys)
            houses = result[0]
            ascendant = result[1][0]  # Ensure this is a single float value
            return houses, ascendant
        except Exception as e:
            logger.error(f"Error in swe.houses(): {e}")
            raise

    def _calculate_body_positions(self):
        """Calculates the positions of the celestial bodies."""
        flags = swe.FLG_SWIEPH + swe.FLG_SPEED
        for body_name, body_id in self.BODIES.items():
            position, _ = swe.calc(self.julian_day, body_id, flags)
            self.positions[body_name] = position[0]

    def _assign_houses_to_bodies(self, houses: List[float]):
        """Assigns houses to the celestial bodies."""
        for body_name, body_longitude in self.positions.items():
            assigned = False
            for i in range(len(houses) - 1):  # Ensure valid indexing
                if houses[i] <= body_longitude < houses[i + 1]:
                    self.body_houses[body_name] = i + 1
                    assigned = True
                    break
                elif houses[i] > houses[i + 1]:  # Handle wrap-around case
                    if body_longitude >= houses[i] or body_longitude < houses[i + 1]:
                        self.body_houses[body_name] = i + 1
                        assigned = True
                        break
            if not assigned:
                logger.warning(f"Could not assign house for {body_name} at longitude {body_longitude}")
                self.body_houses[body_name] = 0  # Or handle as needed

    def _assign_signs_to_bodies(self):
        """Assigns zodiac signs to the celestial bodies."""
        for body_name, body_longitude in self.positions.items():
            self.body_signs[body_name] = self._get_sign_for_position(body_longitude)

    def _get_sign_for_position(self, position: float) -> str:
        """Gets the zodiac sign for a given position."""
        return self.SIGNS[int(position / 30)]

    @staticmethod
    def _create_astrology_individual(zodiac_sign: str, house_number: int) -> AstrologyIndividual:
        return AstrologyIndividual(zodiac_sign=zodiac_sign, house_number=house_number) # type: ignore

class ComparisonHandler:
    """Class to handle the comparison of two astrology charts.

    Attributes:
        planets (AllPlanets): The planetary data.
        p1 (InboundAstrologyChartSchema): The first person's astrology chart.
        p2 (InboundAstrologyChartSchema): The second person's astrology chart.
    """
    def __init__(self, p1: InboundAstrologyChartSchema, p2: InboundAstrologyChartSchema):
        self.planets = PlanetaryData().data
        self.p1: InboundAstrologyChartSchema = p1
        self.p2: InboundAstrologyChartSchema = p2
    
    def compare(self):
        """Compares two astrology charts and returns the comparison result.

        Returns:
            AllComparedWithOverallScore: The comparison result.
        """
        try:
            return self._compare_two_charts()
        except Exception as e:
            logger.error(e)
            # Return a default AllComparedWithOverallScore instance in case of error
            default_compared = AllCompared(
                sun=ComparedSign(),
                moon=ComparedSign(),
                ascendant=ComparedSign(),
                mercury=ComparedSign(),
                venus=ComparedSign(),
                mars=ComparedSign(),
                jupiter=ComparedSign(),
                saturn=ComparedSign(),
                uranus=ComparedSign(),
                neptune=ComparedSign(),
                pluto=ComparedSign()
            )
            return AllComparedWithOverallScore(all_compared=default_compared, overall_score=0.0)

    def _compare_two_signs(self, celestial: Planet, first_zodiac: SIGNS, second_zodiac: SIGNS) -> ComparedSign:
        """Compares two zodiac signs for a given celestial body.

        Args:
            celestial (Planet): The celestial body.
            first_zodiac (SIGNS): The first zodiac sign.
            second_zodiac (SIGNS): The second zodiac sign.

        Returns:
            ComparedSign: The comparison result.
        """
        try:
            celestial_body: IndividualPlanet = self.planets.__getattribute__(celestial.value.lower())
            first_zodiac_in_celestial_body: SignAttributes = celestial_body.signs.__getattribute__(first_zodiac)
            compatibility_data: ComparedSign = first_zodiac_in_celestial_body.compatibility.__getattribute__(second_zodiac)
            return ComparedSign(description=compatibility_data.description, compatibility_score=compatibility_data.compatibility_score)
        except AttributeError as e:
            logger.error(f"AttributeError in _compare_two_signs: {e}")
            return ComparedSign(description="Error: Sign not found", compatibility_score=0.0)

    def _compare_two_charts(self):
        """Compares two astrology charts and calculates the overall compatibility score."""
        try:
            p1_astrology = Astrology(latitude=self.p1.latitude, longitude=self.p1.longitude, birth_datetime=self.p1.birth_datetime)
            p2_astrology = Astrology(latitude=self.p2.latitude, longitude=self.p2.longitude, birth_datetime=self.p2.birth_datetime)
            p1_data = p1_astrology.compute_houses_and_ascendant()
            # logger.info(f"p1_data: {p1_data}")
            p2_data = p2_astrology.compute_houses_and_ascendant()
            
            # Debug prints
            # logger.info(f"p2_data: {p2_data}")

            sun_compatibility = self._compare_two_signs(celestial=Planet.SUN, first_zodiac=p1_data.sun.zodiac_sign, second_zodiac=p2_data.sun.zodiac_sign)
            moon_compatibility = self._compare_two_signs(celestial=Planet.MOON, first_zodiac=p1_data.moon.zodiac_sign, second_zodiac=p2_data.moon.zodiac_sign)
            ascendant_compatibility = self._compare_two_signs(celestial=Planet.ASCENDANT, first_zodiac=p1_data.ascendant, second_zodiac=p2_data.ascendant)
            mercury_compatibility = self._compare_two_signs(celestial=Planet.MERCURY, first_zodiac=p1_data.mercury.zodiac_sign, second_zodiac=p2_data.mercury.zodiac_sign)
            venus_compatibility = self._compare_two_signs(celestial=Planet.VENUS, first_zodiac=p1_data.venus.zodiac_sign, second_zodiac=p2_data.venus.zodiac_sign)
            mars_compatibility = self._compare_two_signs(celestial=Planet.MARS, first_zodiac=p1_data.mars.zodiac_sign, second_zodiac=p2_data.mars.zodiac_sign)
            jupiter_compatibility = self._compare_two_signs(celestial=Planet.JUPITER, first_zodiac=p1_data.jupiter.zodiac_sign, second_zodiac=p2_data.jupiter.zodiac_sign)
            saturn_compatibility = self._compare_two_signs(celestial=Planet.SATURN, first_zodiac=p1_data.saturn.zodiac_sign, second_zodiac=p2_data.saturn.zodiac_sign)
            uranus_compatibility = self._compare_two_signs(celestial=Planet.URANUS, first_zodiac=p1_data.uranus.zodiac_sign, second_zodiac=p2_data.uranus.zodiac_sign)
            neptune_compatibility = self._compare_two_signs(celestial=Planet.NEPTUNE, first_zodiac=p1_data.neptune.zodiac_sign, second_zodiac=p2_data.neptune.zodiac_sign)
            pluto_compatibility = self._compare_two_signs(celestial=Planet.PLUTO, first_zodiac=p1_data.pluto.zodiac_sign, second_zodiac=p2_data.pluto.zodiac_sign)
            
            all_compared = AllCompared(
                sun=sun_compatibility,
                moon=moon_compatibility,
                ascendant=ascendant_compatibility,
                mercury=mercury_compatibility,
                venus=venus_compatibility,
                mars=mars_compatibility,
                jupiter=jupiter_compatibility,
                saturn=saturn_compatibility,
                uranus=uranus_compatibility,
                neptune=neptune_compatibility,
                pluto=pluto_compatibility
            )

            overall_score = (
                sun_compatibility.compatibility_score * 0.2 +
                moon_compatibility.compatibility_score * 0.2 +
                ascendant_compatibility.compatibility_score * 0.1 +
                mercury_compatibility.compatibility_score * 0.1 +
                venus_compatibility.compatibility_score * 0.1 +
                mars_compatibility.compatibility_score * 0.1 +
                jupiter_compatibility.compatibility_score * 0.05 +
                saturn_compatibility.compatibility_score * 0.05 +
                uranus_compatibility.compatibility_score * 0.033 +
                neptune_compatibility.compatibility_score * 0.033 +
                pluto_compatibility.compatibility_score * 0.033
            )
            total_weight = 1.0

            normalized_score = (overall_score / total_weight) * 10
            formatted_score = round(normalized_score, 2)
            result = AllComparedWithOverallScore(all_compared=all_compared, overall_score=formatted_score)
            return result
        except Exception as e:
            logger.error(f"Error in _compare_two_charts: {e}")
            raise