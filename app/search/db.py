from datetime import UTC, datetime

from app.posts.schemas import PostResponse, SearchPostsRequest
from app.search.schemas import SearchUserResponse
from app.shared.neo4j import driver
from app.shared.settings import settings_model
from app.users.schemas import SimpleUserResponse


async def search_posts(user_id: str, search_query: SearchPostsRequest, exclude_post_ids: list[str] = [], limit: int = 30) -> list[PostResponse]:
    base_query = """
    MATCH (user:User {user_id: $user_id})
    MATCH (post:Post)
    WHERE post.post_id NOT IN $exclude_post_ids

    // Check for blocks and privacy
    MATCH (poster:User)-[:POSTED]->(post)
    WHERE NOT (poster)-[:BLOCKS]-(user)
        AND (NOT poster.account_private OR (user)-[:FOLLOWS]->(poster))

    // Apply date filters
    WHERE ($from_date IS NULL OR post.created_at >= $from_date)
        AND ($to_date IS NULL OR post.created_at <= $to_date)

    // Apply profile filters
    WHERE ($profiles IS NULL OR poster.user_id IN $profiles)

    // Apply following_only filter
    WHERE (NOT $following_only OR (user)-[:FOLLOWS]->(poster))

    // Apply must_contain filter and exclude filters
    WHERE ALL(word IN $must_contain WHERE toLower(post.content) CONTAINS toLower(word))
        AND NONE(word IN $exclude WHERE toLower(post.content) CONTAINS toLower(word))
    """

    params: dict[str, str | bool | datetime | list[str] | None | int]  = {
        "user_id": user_id,
        "exclude_post_ids": exclude_post_ids,
        "from_date": search_query.from_date.isoformat() if search_query.from_date else None,
        "to_date": search_query.to_date.isoformat() if search_query.to_date else None,
        "profiles": search_query.profiles,
        "following_only": search_query.following_only,
        "must_contain": search_query.must_contain or [],
        "exclude": search_query.exclude or [],
        "current_date": datetime.now(UTC).date().isoformat(),
    }

    if search_query.general_string:
        base_query += """
        CALL apoc.ml.openai.embedding([$general_string], $apiKey, {
            endpoint: $endpoint,
            apiVersion: $apiVersion,
            apiType: $apiType
            model: $model,
            dimensions: $dimensions,
            encoding_format: $encoding_format
        }) YIELD embedding
        WITH user, post, vector_similarity(embedding, post.embedding) AS similarity
        """

        params.update({
            "general_string": search_query.general_string,
            "apiKey": settings_model.azure.openai.api_key,
            "endpoint": settings_model.azure.openai.endpoint,
            "apiVersion": settings_model.azure.openai.embedding.version,
            "apiType": "AZURE",
            "model": "text-embedding-3-large",
            "dimensions": 256,
            "encoding_format": "float"
        })
    else:
        base_query += """
        WITH user, post, poster, 0 AS similarity
        """
    base_query += """
    // Calculate recency score
    WITH user, post, poster, similarity,
        1 / (1 + duration.inDays(date(post.created_at), date($current_date)).days) AS recency_score


    // Calculate final score
    WITH user, post, poster, (similarity * 3 + recency_score) AS score
    ORDER BY score DESC
    LIMIT $limit

    // Fetch quoted and replied posts
    OPTIONAL MATCH (post)-[:QUOTED]->(quoted_post:Post)<-[:POSTED]-(quoted_poster:User)
    WHERE NOT (user)-[:BLOCKS]-(quoted_poster)
        AND (NOT quoted_poster.account_private OR (user)-[:FOLLOWS]->(quoted_poster))

    OPTIONAL MATCH (post)-[:REPLIED]->(replied_post:Post)<-[:POSTED]-(replied_poster:User)
    WHERE NOT (user)-[:BLOCKS]-(replied_poster)
        AND (NOT replied_poster.account_private OR (user)-[:FOLLOWS]->(replied_poster))

    RETURN post, poster, quoted_post, quoted_poster, replied_post, replied_poster, score
    ORDER BY score DESC
    """
    params["limit"] = limit

    async with driver.session() as session:
        result = await session.run(
            base_query,
            params,
        )
        records = await result.data()
        posts: list[PostResponse] = []
        for record in records:
            post_data = record["post"]
            poster_data = record["poster"]
            quoted_post = None

            if record["quoted_post"]:
                quoted_post = PostResponse(
                    **record["quoted_post"],
                    poster=SimpleUserResponse(**record["quoted_poster"]),
                    quoted_post=None,
                    replied_post=None,
                )

            replied_post = None
            if record["replied_post"]:
                replied_post = PostResponse(
                    **record["replied_post"],
                    poster=SimpleUserResponse(**record["replied_poster"]),
                    quoted_post=None,
                    replied_post=None,
                )

            post = PostResponse(
                **post_data,
                poster=SimpleUserResponse(**poster_data),
                quoted_post=quoted_post,
                replied_post=replied_post,
            )
            posts.append(post)
        return posts

async def search_users(user_id: str, search_query: str, exclude_user_ids: list[str] = [], limit: int = 30) -> SearchUserResponse:
    query = """
    MATCH (user:User {user_id: $user_id})
    MATCH (potential_user:User)
    WHERE NOT potential_user.user_id IN $exclude_user_ids
      AND NOT (user)-[:BLOCKS|MUTES]-(potential_user)
      AND user <> potential_user

    // Similarity calculation
    CALL apoc.ml.openai.embedding([$search_query], $apiKey, {
        endpoint: $endpoint,
        apiVersion: $apiVersion,
        apiType: $apiType,
        model: $model,
        dimensions: $dimensions,
        encoding_format: $encoding_format
    }) YIELD embedding
    WITH user, potential_user, vector_similarity(embedding, potential_user.embedding) AS similarity

    // Network connections
    OPTIONAL MATCH (user)-[:FOLLOWS]->(followee:User)-[:FOLLOWS]->(potential_user)
    OPTIONAL MATCH (user)-[:FOLLOWS]->(followee:User)<-[:FOLLOWS]-(potential_user)
    OPTIONAL MATCH (user)<-[:FOLLOWS]-(follower:User)-[:FOLLOWS]->(potential_user)
    OPTIONAL MATCH (user)<-[:FOLLOWS]-(follower:User)<-[:FOLLOWS]-(potential_user)
    WITH user, potential_user, similarity,
         COUNT(DISTINCT followee) AS common_followees,
         COUNT(DISTINCT follower) AS common_followers

    // Location similarity
    WITH user, potential_user, similarity, common_followees, common_followers,
    CASE
        WHEN user.recent_location IS NOT NULL AND potential_user.recent_location IS NOT NULL
        THEN point.distance(point({latitude: user.recent_location[0], longitude: user.recent_location[1]}),
                            point({latitude: potential_user.recent_location[0], longitude: potential_user.recent_location[1]}))
        WHEN user.profile_location IS NOT NULL AND potential_user.profile_location IS NOT NULL
        THEN point.distance(point({latitude: user.profile_location[0], longitude: user.profile_location[1]}),
                            point({latitude: potential_user.profile_location[0], longitude: potential_user.profile_location[1]}))
        ELSE NULL
    END AS location_distance

    // Common schools
    OPTIONAL MATCH (user)-[:ATTENDED]->(school:School)<-[:ATTENDED]-(potential_user)
    WITH user, potential_user, similarity, common_followees, common_followers, location_distance,
         COUNT(DISTINCT school) AS common_schools

    // Interaction with posts (LIKED and REPOSTED)
    OPTIONAL MATCH (user)-[like_repost:LIKED|REPOSTED]->(:Post)<-[:POSTED]-(potential_user)

    // Interaction with posts (QUOTED and REPLIED)
    OPTIONAL MATCH (user)-[:POSTED]->(:Post)-[quote_reply:QUOTED|REPLIED]->(:Post)<-[:POSTED]-(potential_user)

    WITH user, potential_user, similarity, common_followees, common_followers, location_distance, common_schools,
         COUNT(DISTINCT like_repost) + COUNT(DISTINCT quote_reply) AS interaction_count

    // Chat interactions
    OPTIONAL MATCH (user)-[:PARTICIPATES_IN]->(conversation:Conversation)<-[:PARTICIPATES_IN]-(potential_user)
    OPTIONAL MATCH (user)-[:SENT]->(message:Message)-[:IN]->(conversation:Conversation)<-[:PARTICIPATES_IN]-(potential_user)
    WITH user, potential_user, similarity, common_followees, common_followers, location_distance, common_schools, interaction_count,
         COUNT(DISTINCT conversation) AS shared_conversations,
         COUNT(DISTINCT message) AS messages_sent

    // Dating interactions
    OPTIONAL MATCH (user)-[swiped_right:SWIPED_RIGHT]->(potential_user)
    OPTIONAL MATCH (user)-[dating_match:DATING_MATCH]-(potential_user)
    WITH user, potential_user, similarity, common_followees, common_followers, location_distance, common_schools,
         interaction_count, shared_conversations, messages_sent,
         COUNT(swiped_right) AS swiped_right_count,
         COUNT(dating_match) AS dating_match_count

    // Check if already following
    OPTIONAL MATCH (user)-[follows:FOLLOWS]->(potential_user)
    WITH user, potential_user, similarity, common_followees, common_followers, location_distance, common_schools,
         interaction_count, shared_conversations, messages_sent, swiped_right_count, dating_match_count,
         CASE WHEN follows IS NOT NULL THEN 1 ELSE 0 END AS is_following

    // Calculate weighted score
    WITH user, potential_user,
         similarity * 10 +
         common_followees * 2 +
         common_followers * 2 +
         CASE WHEN location_distance IS NOT NULL THEN 5 * EXP(-location_distance / 10000) ELSE 0 END +
         common_schools * 3 +
         interaction_count * 2 +
         shared_conversations * 3 +
         messages_sent * 0.5 +
         swiped_right_count * 5 +
         dating_match_count * 10 +
         is_following * 20 AS score

    RETURN potential_user {
        .user_id,
        .username,
        .display_name,
        .profile_photo,
        .created_at
    } AS recommended_user,
    score
    ORDER BY score DESC
    LIMIT $limit
    """

    params = {
        "user_id": user_id,
        "search_query": search_query,
        "exclude_user_ids": exclude_user_ids,
        "limit": limit,
        "apiKey": settings_model.azure.openai.api_key,
        "endpoint": settings_model.azure.openai.endpoint,
        "apiVersion": settings_model.azure.openai.embedding.version,
        "apiType": "AZURE",
        "model": "text-embedding-3-large",
        "dimensions": 256,
        "encoding_format": "float"
    }

    async with driver.session() as session:
        result = await session.run(query, params)
        records = await result.data()
        users = [
            SimpleUserResponse(
                user_id=record["recommended_user"]["user_id"],
                username=record["recommended_user"]["username"],
                display_name=record["recommended_user"]["display_name"],
                profile_photo=record["recommended_user"].get("profile_photo"),
                created_at=datetime.fromisoformat(record["recommended_user"]["created_at"]),
            )
            for record in records
        ]
    return SearchUserResponse(users=users)