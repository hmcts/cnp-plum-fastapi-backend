"""seed_python_recipe

Revision ID: a8dbb031b86c
Revises: 
Create Date: 2026-06-16 09:52:29.245826

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a8dbb031b86c'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS recipe (
            id          VARCHAR(256) NOT NULL PRIMARY KEY,
            user_id     VARCHAR(256) NOT NULL,
            name        VARCHAR(256) NOT NULL,
            ingredients TEXT         NOT NULL,
            method      TEXT         NOT NULL
        )
    """)
    op.execute("""
        INSERT INTO recipe (id, user_id, name, ingredients, method)
        VALUES (
            'seed-recipe-2',
            'seed-user',
            'Seeded Vegetable Curry',
            'chickpeas,spinach,coconut milk,curry paste,onion,garlic',
            'Fry onion and garlic. Add curry paste. Add chickpeas and coconut milk. Simmer 15 mins. Stir in spinach.'
        )
        ON CONFLICT (id) DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DELETE FROM recipe WHERE id = 'seed-recipe-2'")
