import asyncio

from dotenv import load_dotenv
from fastapi import HTTPException, status
from loguru import logger
from neo4j import AsyncGraphDatabase

load_dotenv()
from app.shared.settings import settings_model

driver = AsyncGraphDatabase.driver(
    str(settings_model.neo4j.uri),
    auth=(settings_model.neo4j.username, settings_model.neo4j.password),
)

async def set_user_embedding():
    query = """
    CREATE VECTOR INDEX `user-embedding` IF NOT EXISTS
    FOR (user:User) ON (user.embedding)
    OPTIONS {
        indexConfig: {
            `vector.dimensions`: 256,
            `vector.similarity_function`: 'cosine'
            }
        };
    """
    await driver.session().run(query)
    logger.info("Created user embedding index.")
    query = """
    MATCH (user:User)
    WHERE user.embedding IS NULL
    WITH collect(user) AS users
    UNWIND users AS u
    WITH u, apoc.text.join([
        'DISPLAY NAME: ', u.display_name, ' | ',
        'FIRST NAME: ', u.first_name, ' | ',
        'LAST NAME: ', u.last_name, ' | ',
        'USERNAME: ', u.username, ' | ',
        'DATING BIO: ', u.dating_bio, ' | '
    ], '') AS bio
    CALL apoc.ml.openai.embedding([bio], $apiKey, {
        endpoint: $endpoint,
        apiVersion: $apiVersion,
        apiType: $apiType,
        model: $model,
        dimensions: $dimensions,
        encoding_format: $encoding_format
    }) YIELD embedding
    CALL db.create.setNodeVectorProperty(u, 'embedding', embedding)
    RETURN count(*) AS updatedUsers
    """
    res = await driver.session().run(query, {
        "apiKey": settings_model.azure.openai.api_key,
        "endpoint": settings_model.azure.openai.endpoint,
        "apiVersion": settings_model.azure.openai.embedding.version,
        "apiType": "AZURE",
        "model": "text-embedding-ada-002",
        "dimensions": 256,
        "encoding_format": "float",
    })
    record = await res.single()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Failed to set user embeddings.",
        )
    return record["updatedUsers"]


async def set_post_embedding():
    async with driver.session() as session:

        query = """
        CREATE VECTOR INDEX `post-embedding` IF NOT EXISTS
        FOR (post:Post) ON (post.embedding)
        OPTIONS {
            indexConfig: {
                `vector.dimensions`: 256,
                `vector.similarity_function`: 'cosine'
            }
        };
        """
        await session.run(query)
        logger.info("Created post embedding index.")

        query = """
        MATCH (post:Post)
        WHERE post.embedding IS NULL
        WITH collect(post) AS posts
        UNWIND posts AS p
        CALL apoc.ml.openai.embedding([p.content], $apiKey, {
            endpoint: $endpoint,
            apiVersion: $apiVersion,
            apiType: $apiType,
            model: $model,
            dimensions: $dimensions,
            encoding_format: $encoding_format
        }) YIELD embedding
        CALL db.create.setNodeVectorProperty(p, 'embedding', embedding)
        RETURN count(posts) AS updatedPosts
        """

        res = await session.run(
            query,
            {
                "apiKey": settings_model.azure.openai.api_key,
                "endpoint": settings_model.azure.openai.endpoint,
                "apiVersion": settings_model.azure.openai.embedding.version,
                "apiType": "AZURE",
                "model": "text-embedding-3-large",
                "dimensions": 256,
                "encoding_format": "float",
            },
        )
        record = await res.single()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Failed to set post embeddings.",
            )
        return record["updatedPosts"]

async def initialize_indices():
    r1 = await set_user_embedding()
    r2 = await set_post_embedding()
    logger.info(f"Updated {r1} users and {r2} posts.")

res = asyncio.run(initialize_indices())
logger.info(f"Updated {res} posts.")

async def set_vector_indices():
    pass
