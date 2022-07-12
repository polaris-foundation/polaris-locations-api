"""Foreign key ID columns have fixed width

Revision ID: b6a60649a763
Revises: 3105cbbdfe95
Create Date: 2020-12-03 15:37:08.186011

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b6a60649a763"
down_revision = "3105cbbdfe95"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "location",
        "parent_id",
        existing_type=sa.String,
        type_=sa.String(length=36),
        existing_nullable=True,
    )
    op.alter_column(
        "location_product",
        "location_uuid",
        existing_type=sa.String,
        type_=sa.String(length=36),
        existing_nullable=True,
    )


def downgrade():
    op.alter_column(
        "location_product",
        "location_uuid",
        existing_type=sa.String(36),
        type_=sa.String,
        existing_nullable=True,
    )
    op.alter_column(
        "location",
        "parent_id",
        existing_type=sa.String(36),
        type_=sa.String,
        existing_nullable=True,
    )
