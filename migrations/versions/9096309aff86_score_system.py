"""score_system


Revision ID: 9096309aff86
Revises: b6a60649a763
Create Date: 2020-12-09 15:50:01.044584

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9096309aff86"
down_revision = "b6a60649a763"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "location", sa.Column("score_system_default", sa.String(), nullable=True)
    )


def downgrade():
    op.drop_column("location", "score_system_default")
