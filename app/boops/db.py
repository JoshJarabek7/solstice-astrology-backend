from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException, status

from app.boops.schemas import (BoopEvent, BoopListRequest, BoopListResponse,
                               BoopRequest, BoopSingle)
from app.shared.neo4j import driver
from app.users.schemas import SimpleUserResponse


async def get_boop_list(boop_request: BoopListRequest) -> BoopListResponse:
    query = """
    MATCH (user:User {user_id: $user_id})-[r:BOOP_RELATIONSHIP]-(booper:User)
    RETURN r {
        .boop_id,
        .total_boops,
        .turn_id,
        .created_at,
        .updated_at
        } AS boop,
        booper {
        .user_id,
        .username,
        .display_name,
        .profile_photo,
        .created_at
        } AS booper

    LIMIT $limit
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "user_id": boop_request.user_id,
                "limit": boop_request.limit + 1,
            }
        )
        records = await result.data()
        if not records:
            return BoopListResponse(
                boops=[],
                has_more=False,
            )
        boops: list[BoopSingle] = []
        for record in records:
            boop = record["boop"]
            booper = record["booper"]
            boops.append(
                BoopSingle(
                    total_boops=boop["total_boops"],
                    booper=SimpleUserResponse(**booper),
                    boop_id=boop["boop_id"],
                    turn_id=boop["turn_id"],
                    created_at=datetime.fromisoformat(boop["created_at"]),
                    updated_at=datetime.fromisoformat(boop["updated_at"]),
                )
            )
        return BoopListResponse(
            boops=boops,
            has_more=len(boops) > boop_request.limit,
        )


async def boop_user(request: BoopRequest) -> BoopEvent:
    query = """
    MATCH (requesting_user:User {user_id: $requesting_user_id})
    MATCH (target_user:User {user_id: $target_user_id})
    WHERE (
        ((target_user)-[:FOLLOWS]->(requesting_user) AND (requesting_user)-[:FOLLOWS]->(target_user))
        OR (requesting_user)-[:BOOP_RELATIONSHIP]-(target_user)
    )
    AND (NOT (requesting_user)-[:BLOCKS]-(target_user))
    MERGE (requesting_user)-[r:BOOP_RELATIONSHIP]->(target_user)
    ON CREATE SET
        r.boop_id = $boop_id,
        r.total_boops = 1,
        r.created_at = $created_at,
        r.updated_at = $updated_at,
        r.turn_id = target_user.user_id
    ON MATCH SET
        r.total_boops = r.total_boops + 1,
        r.updated_at = $updated_at,
        r.turn_id = target_user.user_id
    RETURN r {
        .boop_id,
        .total_boops,
        .turn_id,
        .created_at,
        .updated_at
    } AS boop,
    requesting_user {
        .user_id,
        .username,
        .display_name,
        .profile_photo,
        .created_at
    } AS booper,
    target_user {
        .user_id
    } AS booped
    """

    current_time = datetime.now(UTC).isoformat()

    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "requesting_user_id": request.requesting_user_id,
                "target_user_id": request.target_user_id,
                "boop_id": str(uuid4()),
                "created_at": current_time,
                "updated_at": current_time,
            }
        )
        record = await result.single()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found or conditions not met.",
            )
        boop_id = record["boop"]["boop_id"]
        total_boops = record["boop"]["total_boops"]
        booper = SimpleUserResponse(**record["booper"])
        booped_user_id = record["booped"]["user_id"]
        turn_id = record["booped"]["turn_id"]

        return BoopEvent(
            boop_id=boop_id,
            total_boops=total_boops,
            booper=booper,
            booped_user_id=booped_user_id,
            turn_id=turn_id,
        )