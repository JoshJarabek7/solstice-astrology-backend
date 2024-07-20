from unittest.mock import AsyncMock

import pytest
import pytest_mock
from dotenv import load_dotenv
from pytest_asyncio import is_async_test

load_dotenv()

@pytest.fixture
async def mock_neo4j_session(mocker: pytest_mock.MockerFixture):
    # Create an AsyncMock for the session
    session = AsyncMock()
    session.run.return_value.single.return_value = None
    session.run.return_value.data.return_value = []

    # Mock the __aenter__ and __aexit__ methods for the async context manager
    session.__aenter__.return_value = session
    session.__aexit__.return_value = None

    # Patch the driver.session method to return the mocked session
    mocker.patch('app.shared.neo4j.driver.session', return_value=session)
    return session

def pytest_collection_modifyitems(items: list[pytest.Function]):
    for item in items:
        if is_async_test(item):
            item.add_marker(pytest.mark.asyncio)

@pytest.fixture(autouse=True)
def mock_driver(mocker: pytest_mock.MockerFixture):
    mocker.patch('app.shared.neo4j.driver', new_callable=AsyncMock)
