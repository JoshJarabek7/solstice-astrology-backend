
from datetime import datetime

from fastapi import HTTPException

from app.astrology.schemas import AstrologyDetailsCompared, AstrologyDetailsSingleUser
from app.astrology.utils import (
    assign_signs_to_bodies,
    calculate_body_positions,
    calculate_houses,
    calculate_julian_day,
    get_astrology_details_for_body_single_user,
    get_astrology_details_for_comparison,
    get_sign_for_position,
    local_to_utc,
)
from app.shared.neo4j import driver


async def get_astrology_profile(requester_id: str, target_user_id: str) -> AstrologyDetailsSingleUser:
    async with driver.session() as session:
        query = """
        MATCH (requesting_user:User {user_id: $requester_id})
        MATCH (target_user:User {user_id: $target_user_id})
        OPTIONAL MATCH (requesting_user)-[:BLOCKS]-(target_user)
        WITH requesting_user, target_user, COUNT(DISTINCT target_user) AS block_count
        WHERE block_count = 0
        RETURN target_user.sun AS sun,
            target_user.moon AS moon,
            target_user.ascendant AS ascendant,
            target_user.mercury AS mercury,
            target_user.venus AS venus,
            target_user.mars AS mars,
            target_user.jupiter AS jupiter,
            target_user.saturn AS saturn,
            target_user.uranus AS uranus,
            target_user.neptune AS neptune,
            target_user.pluto AS pluto,
            target_user.birth_datetime_utc AS birth_datetime_utc,
            target_user.birth_location AS birth_location
        """
        result = await session.run(
            query,
            {
                "target_user_id": target_user_id,
                "requester_id": requester_id,
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(
                status_code=404,
                detail="User or astrology details not found.",
            )

        sun = get_astrology_details_for_body_single_user("sun", record["sun"])
        moon = get_astrology_details_for_body_single_user("moon", record["moon"])
        ascendant = get_astrology_details_for_body_single_user(
            "ascendant",
            record["ascendant"],
        )
        mercury = get_astrology_details_for_body_single_user(
            "mercury",
            record["mercury"],
        )
        venus = get_astrology_details_for_body_single_user("venus", record["venus"])
        mars = get_astrology_details_for_body_single_user("mars", record["mars"])
        jupiter = get_astrology_details_for_body_single_user(
            "jupiter",
            record["jupiter"],
        )
        saturn = get_astrology_details_for_body_single_user("saturn", record["saturn"])
        uranus = get_astrology_details_for_body_single_user("uranus", record["uranus"])
        neptune = get_astrology_details_for_body_single_user(
            "neptune",
            record["neptune"],
        )
        pluto = get_astrology_details_for_body_single_user("pluto", record["pluto"])

        return AstrologyDetailsSingleUser(
            sun=sun,
            moon=moon,
            ascendant=ascendant,
            mercury=mercury,
            venus=venus,
            mars=mars,
            jupiter=jupiter,
            saturn=saturn,
            uranus=uranus,
            neptune=neptune,
            pluto=pluto,
        )


async def create_astrology_chart(user_id: str,birth_datetime: datetime, latitude: float, longitude: float) -> None:
    birth_datetime_utc = local_to_utc(birth_datetime, latitude, longitude)
    julian_day = calculate_julian_day(birth_datetime_utc)
    positions = calculate_body_positions(julian_day)
    body_signs: dict[str, str] = assign_signs_to_bodies(positions)
    _, ascmc = calculate_houses(julian_day, latitude, longitude, "O")
    body_signs["ascendant"] = get_sign_for_position(ascmc[0])
    async with driver.session() as session:
        query = """
        MATCH (user:User {user_id: $user_id})
        SET user.birth_datetime_utc = $birth_datetime_utc,
            user.birth_location = point({latitude: $latitude, longitude: $longitude}),
            user.sun = $sun,
            user.moon = $moon,
            user.ascendant = $ascendant,
            user.mercury = $mercury,
            user.venus = $venus,
            user.mars = $mars,
            user.jupiter = $jupiter,
            user.saturn = $saturn,
            user.uranus = $uranus,
            user.neptune = $neptune,
            user.pluto = $pluto
        """
        await session.run(
            query,
            {
                "user_id": user_id,
                "birth_datetime_utc": birth_datetime_utc,
                "latitude": latitude,
                "longitude": longitude,
                "sun": body_signs["Sun"],
                "moon": body_signs["Moon"],
                "ascendant": body_signs["ascendant"],
                "mercury": body_signs["Mercury"],
                "venus": body_signs["Venus"],
                "mars": body_signs["Mars"],
                "jupiter": body_signs["Jupiter"],
                "saturn": body_signs["Saturn"],
                "uranus": body_signs["Uranus"],
                "neptune": body_signs["Neptune"],
                "pluto": body_signs["Pluto"],
            },
        )

async def compare_astrology_couple(requester_id: str, target_user_id: str) -> AstrologyDetailsCompared:
    async with driver.session() as session:
        query = """
        MATCH (requester:User {user_id: $requester_id}))
        MATCH (target:User {user_id: $target_id})
        OPTIONAL MATCH (requester)-[:BLOCKS]-(target)
        WITH requester, target, COUNT(target) AS block_count
        WHERE block_count = 0
        RETURN target.sun AS sun,
            target.moon AS moon,
            target.ascendant AS ascendant,
            target.mercury AS mercury,
            target.venus AS venus,
            target.mars AS mars,
            target.jupiter AS jupiter,
            target.saturn AS saturn,
            target.uranus AS uranus,
            target.neptune AS neptune,
            target.pluto AS pluto,
            requester.sun AS requester_sun,
            requester.moon AS requester_moon,
            requester.ascendant AS requester_ascendant,
            requester.mercury AS requester_mercury,
            requester.venus AS requester_venus,
            requester.mars AS requester_mars,
            requester.jupiter AS requester_jupiter,
            requester.saturn AS requester_saturn,
            requester.uranus AS requester_uranus,
            requester.neptune AS requester_neptune,
            requester.pluto AS requester_pluto,
        """
        result = await session.run(
            query,
            {
                "target_user_id": target_user_id,
                "requester_id": requester_id,
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(
                status_code=404,
                detail="User or astrology details not found.",

            )
        sun = get_astrology_details_for_comparison(
            "sun",
            record["requester_sun"],
            record["sun"],
        )
        moon = get_astrology_details_for_comparison(
            "moon",
            record["requester_moon"],
            record["moon"],
        )
        ascendant = get_astrology_details_for_comparison(
            "ascendant",
            record["requester_ascendant"],
            record["ascendant"],
        )
        mercury = get_astrology_details_for_comparison(
            "mercury",
            record["requester_mercury"],
            record["mercury"],
        )
        venus = get_astrology_details_for_comparison(
            "venus",
            record["requester_venus"],
            record["venus"],
        )
        mars = get_astrology_details_for_comparison(
            "mars",
            record["requester_mars"],
            record["mars"],
        )
        jupiter = get_astrology_details_for_comparison(
            "jupiter",
            record["requester_jupiter"],
            record["jupiter"],
        )
        saturn = get_astrology_details_for_comparison(
            "saturn",
            record["requester_saturn"],
            record["saturn"],
        )
        uranus = get_astrology_details_for_comparison(
            "uranus",
            record["requester_uranus"],
            record["uranus"],
        )
        neptune = get_astrology_details_for_comparison(
            "neptune",
            record["requester_neptune"],
            record["neptune"],
        )
        pluto = get_astrology_details_for_comparison(
            "pluto",
            record["requester_pluto"],
            record["pluto"],
        )
        total_score = (
            (sun.score * 0.2)
            + (moon.score * 0.2)
            + (ascendant.score * 0.1)
            + (mercury.score * 0.1)
            + (venus.score * 0.1)
            + (mars.score * 0.1)
            + (jupiter.score * 0.05)
            + (saturn.score * 0.05)
            + (uranus.score * 0.033)
            + (neptune.score * 0.033)
            + (pluto.score * 0.033)
        )
        return AstrologyDetailsCompared(
            sun=sun,
            moon=moon,
            ascendant=ascendant,
            mercury=mercury,
            venus=venus,
            mars=mars,
            jupiter=jupiter,
            saturn=saturn,
            uranus=uranus,
            neptune=neptune,
            pluto=pluto,
            total_score=total_score,
        )
