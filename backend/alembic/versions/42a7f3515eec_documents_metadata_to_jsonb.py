"""documents metadata to jsonb

Revision ID: 42a7f3515eec
Revises: b666931c1668
Create Date: 2026-09-22 10:11:39.512635

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '42a7f3515eec'
down_revision: Union[str, None] = 'b666931c1668'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE documents ALTER COLUMN metadata TYPE jsonb USING metadata::jsonb"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE documents ALTER COLUMN metadata TYPE json USING metadata::json"
    )
