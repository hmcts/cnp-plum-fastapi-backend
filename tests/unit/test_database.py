import pytest
from app.database import get_db


@pytest.mark.asyncio
async def test_get_db_raises_when_engine_not_initialised():
    gen = get_db()
    with pytest.raises(RuntimeError, match="Database engine not initialised"):
        await gen.__anext__()
