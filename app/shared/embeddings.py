import asyncio
import json
import os
import re
import sys
from datetime import UTC, datetime, timedelta
from enum import IntEnum
from math import atan2, cos, radians, sin, sqrt
from pathlib import Path
from typing import Any, LiteralString, Optional, TypeVar, cast
from uuid import UUID, uuid4

import httpx
import jwt
import neo4j
import pytz
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from dotenv import load_dotenv
from fastapi import (Depends, FastAPI, HTTPException, Query, Security,
                     WebSocket, WebSocketException, status)
from fastapi.security import OAuth2PasswordBearer
from faststream.kafka.fastapi import KafkaRouter
from jwt.algorithms import RSAAlgorithm
from loguru import logger
from neo4j import AsyncGraphDatabase
from neo4j.exceptions import Neo4jError
from openai import AsyncAzureOpenAI
from pydantic import BaseModel, EmailStr
from settings import settings_model
from swisseph import (FLG_SPEED, FLG_SWIEPH, GREG_CAL, JUPITER, MARS, MERCURY,
                      MOON, NEPTUNE, PLUTO, SATURN, SUN, URANUS, VENUS, calc,
                      houses, julday)
from timezonefinder import TimezoneFinder


async def get_embedding(text: str) -> list[float]:
    """Get the embedding for a given text."""
    client = AsyncAzureOpenAI(
        api_key=settings_model.azure.openai.api_key,
        api_version="2024-02-01",
        azure_endpoint=settings_model.azure.openai.endpoint,
    )
    response = await client.embeddings.create(input=text, model="text-embedding-3-large", dimensions=256, encoding_format="float")
    return response.data[0].embedding
