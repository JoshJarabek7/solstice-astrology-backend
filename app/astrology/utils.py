
from datetime import datetime
from typing import cast

import pytz
from loguru import logger
from swisseph import (
    FLG_SPEED,
    FLG_SWIEPH,
    GREG_CAL,
    JUPITER,
    MARS,
    MERCURY,
    MOON,
    NEPTUNE,
    PLUTO,
    SATURN,
    SUN,
    URANUS,
    VENUS,
    calc,
    houses,
    julday,
)
from timezonefinder import TimezoneFinder

from app.astrology.data import astrology_data
from app.astrology.schemas import *


def get_timezone_for_user(latitude: float, longitude: float) -> pytz.BaseTzInfo:
    """Get the timezone for a given latitude and longitude.

    Args:
        latitude (float): The latitude of the user.
        longitude (float): The longitude of the user.

    Returns:
        pytz.BaseTzInfo: The timezone for the given latitude and longitude.
    """
    tf = TimezoneFinder()
    timezone_str = tf.certain_timezone_at(lng=longitude, lat=latitude)
    if not isinstance(timezone_str, str):
        error_message = "Timezone could not be determined."
        raise TypeError(error_message) from None
    return pytz.timezone(timezone_str)


def local_to_utc(
    datetime_of_user: datetime,
    lat: float,
    lon: float,
) -> datetime:
    """Convert a local datetime to UTC.

    Args:
        datetime_of_user (datetime.datetime): The local datetime to convert.
        lat (float): The latitude of the user.
        lon (float): The longitude of the user.

    Returns:
        datetime.datetime: The converted UTC datetime.
    """
    timezone = get_timezone_for_user(lat, lon)
    local_dt = datetime_of_user.astimezone(timezone)
    return local_dt.astimezone(pytz.utc)


def calculate_julian_day(utc_datetime: datetime) -> float:
    """Calculate the Julian day for a given UTC datetime.

    Args:
        utc_datetime (datetime): The UTC datetime.

    Returns:
        float: The Julian day.
    """
    try:
        return julday(
            utc_datetime.year,
            utc_datetime.month,
            utc_datetime.day,
            utc_datetime.hour + utc_datetime.minute / 60.0 + utc_datetime.second / 3600.0,
            GREG_CAL,
        )

    except ValueError as e:
        raise ValueError(
            "An error occurred while calculating the Julian day: " + str(e),
        ) from e

BODIES: dict[str, int] = {
    "Sun": SUN,
    "Moon": MOON,
    "Mercury": MERCURY,
    "Venus": VENUS,
    "Mars": MARS,
    "Jupiter": JUPITER,
    "Saturn": SATURN,
    "Uranus": URANUS,
    "Neptune": NEPTUNE,
    "Pluto": PLUTO,
}


SIGNS = [
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
]


def calculate_body_positions(julian_day: float) -> dict[str, float]:
    """Calculate the positions of the celestial bodies.

    Args:
        julian_day (float): The Julian day.

    Returns:
        dict[str, float]: The positions of the celestial bodies.
    """
    positions: dict[str, float] = {}
    flags: int = FLG_SWIEPH + FLG_SPEED
    for body_name, body_id in BODIES.items():
        position, _ = cast(tuple[tuple[float], int], calc(julian_day, body_id, flags))
        positions[body_name] = position[0]
    return positions


def assign_houses_to_bodies(
    static_houses: list[float],
    body_houses: dict[str, int],
    positions: dict[str, float],
) -> dict[str, int]:
    """Assign houses to the celestial bodies.

    Args:
        static_houses (list[float]): The static houses.
        body_houses (dict[str, int]): The body houses.
        positions (dict[str, float]): The positions of the celestial bodies.

    Returns:
        dict[str, int]: The body houses.
    """
    for body_name, body_longitude in positions.items():
        assigned = False
        for i in range(len(static_houses) - 1):
            if static_houses[i] <= body_longitude < static_houses[i + 1]:
                body_houses[body_name] = i + 1
                assigned = True
            elif static_houses[i] > static_houses[i + 1]:
                if (body_longitude >= static_houses[i]) or (body_longitude < static_houses[i + 1]):
                    body_houses[body_name] = i + 1
                    assigned = True
            if not assigned:
                logger.warning(
                    "Could not assign house for %s at longitude %f",
                    body_name,
                    body_longitude,
                )
                body_houses[body_name] = 0  # Or handle as needed
    return body_houses


def get_sign_for_position(position: float) -> str:
    """Get the sign for a given position.

    Args:
        position (float): The position.

    Returns:
        str: The sign.
    """
    return SIGNS[int(position / 30)]


def assign_signs_to_bodies(
    positions: dict[str, float],
) -> dict[str, str]:
    """Assign signs to the celestial bodies.

    Args:
        positions (dict[str, float]): The positions of the celestial bodies.
    """
    body_signs: dict[str, str] = {}
    for body_name, body_longitude in positions.items():
        body_signs[body_name] = get_sign_for_position(body_longitude)
    return body_signs

# Constants for house systems
house_systems = {
    "A": "A",  # Equal (Ascendant)
    "E": "E",  # Equal (MC)
    "C": "C",  # Campanus
    "K": "K",  # Koch
    "O": "O",  # Porphyry
    "R": "R",  # Regiomontanus
    "T": "T",  # Topocentric
    "V": "V",  # Vehlow Equal
    "W": "W",  # Whole Sign
    "X": "X",  # Axial Rotation System/ Meridian
    "H": "H",  # Horizon/ Azimuthal
    "G": "G",  # Gauquelin Sector
    "M": "M",  # Morinus
    "P": "P",  # Placidus
    "B": "B",  # Alcabitius
    "Q": "Q",  # Carter Polarity/ Dynamic Equal
    "Z": "Z",  # APC Houses
}


def calculate_houses(julian_day: float, lat: float, long: float, house_system: str) -> tuple[list[float], list[float]]:
    hsys = house_systems.get(house_system, "O")  # Default to Porphyry
    try:
        cusps, ascmc = houses(julian_day, lat, long, hsys)
        return cusps, ascmc
    except Exception as e:
        print(f"Error calculating houses: {e}")
        return ([], [])



def get_astrology_details_for_body_single_user(
    celestial_body: str,
    zodiac_sign: str,
) -> AstrologyBodyDetails:
    """Get the details for a single astrology body for a single user.

    Args:
        celestial_body (str): The celestial body.
        zodiac_sign (str): The zodiac sign.

    Returns:
        AstrologyBodyDetails: The details for the astrology body.
    """
    celestial_body_data = astrology_data.__getattribute__(celestial_body)
    body_themes = celestial_body_data.__getattribute__.themes
    body_description = celestial_body_data.__getattribute__.description
    sign_for_body = celestial_body_data.__getattribute__(zodiac_sign)
    sign_description = sign_for_body.description
    sign_traits_for_body = sign_for_body.traits
    return AstrologyBodyDetails(
        body_description=body_description,
        body_themes=body_themes,
        sign=zodiac_sign,
        sign_description=sign_description,
        sign_traits=sign_traits_for_body,
    )


def get_astrology_details_for_comparison(
    celestial_body: str,
    requesting_user_sign: str,
    target_user_sign: str,
) -> AstrologyDetailsComparedDetails:
    """Get the details for comparing two astrology profiles for a single body.

    Args:
        celestial_body (str): The celestial body.
        requesting_user_sign (str): The sign of the requesting user.
        target_user_sign (str): The sign of the target user.

    Returns:
        AstrologyDetailsComparedDetails: The details for comparing two astrology
            profiles for a single body.
    """
    celestial_body_data = astrology_data.__getattribute__(celestial_body)
    requesting_user_body_details = celestial_body_data.__getattribute__(
        requesting_user_sign,
    )
    compatibility_data = requesting_user_body_details.compatibility.__getattribute__(
        target_user_sign,
    )
    celestial_body_description = celestial_body_data.description
    celestial_body_themes = celestial_body_data.themes
    compatibility_description = compatibility_data.description
    compatibility_score = compatibility_data.score
    return AstrologyDetailsComparedDetails(
        body_description=celestial_body_description,
        body_themes=celestial_body_themes,
        requesting_user_sign=requesting_user_sign,
        target_user_sign=target_user_sign,
        description=compatibility_description,
        score=compatibility_score,
    )
