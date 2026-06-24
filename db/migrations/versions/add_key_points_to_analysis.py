from alembic import op
import sqlalchemy as sa

revision = 'add_key_points_analysis'
down_revision = 'c697e6413d08_add_auth_models'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('analyses', sa.Column('key_points', sa.ARRAY(sa.String()), nullable=True))


def downgrade():
    op.drop_column('analyses', 'key_points')