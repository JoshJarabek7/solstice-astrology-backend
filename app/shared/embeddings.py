
from openai import AsyncAzureOpenAI
from settings import settings_model


async def get_embedding(text: str) -> list[float]:
    """Get the embedding for a given text."""
    client = AsyncAzureOpenAI(
        api_key=settings_model.azure.openai.api_key,
        api_version="2024-02-01",
        azure_endpoint=settings_model.azure.openai.endpoint,
    )
    response = await client.embeddings.create(input=text, model="text-embedding-3-large", dimensions=256, encoding_format="float")
    return response.data[0].embedding
