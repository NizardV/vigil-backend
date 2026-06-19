"""add auth models

Revision ID: c697e6413d08
Revises: 001
Create Date: 2026-06-19 18:34:27.235014

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'c697e6413d08'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('users',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('hashed_password', sa.String(length=255), nullable=True),
    sa.Column('is_verified', sa.Boolean(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('totp_secret', sa.String(length=64), nullable=True),
    sa.Column('totp_enabled', sa.Boolean(), nullable=False),
    sa.Column('oauth_provider', sa.String(length=20), nullable=True),
    sa.Column('oauth_id', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_table('email_verification_tokens',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('token', sa.String(length=512), nullable=False),
    sa.Column('expires_at', sa.TIMESTAMP(), nullable=False),
    sa.Column('used', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token')
    )
    op.create_table('refresh_tokens',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('token', sa.String(length=512), nullable=False),
    sa.Column('expires_at', sa.TIMESTAMP(), nullable=False),
    sa.Column('revoked', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token')
    )

    # Clear existing data before adding NOT NULL foreign keys
    op.execute('DELETE FROM feedbacks')
    op.execute('DELETE FROM webhooks')
    op.execute('DELETE FROM themes')

    op.add_column('feedbacks', sa.Column('user_id', sa.UUID(), nullable=True))
    op.alter_column('feedbacks', 'user_id', nullable=False)
    op.create_foreign_key(None, 'feedbacks', 'users', ['user_id'], ['id'], ondelete='CASCADE')

    op.alter_column('sources', 'fetch_interval_hours',
               existing_type=sa.INTEGER(),
               nullable=False,
               existing_server_default=sa.text('2'))

    op.add_column('themes', sa.Column('user_id', sa.UUID(), nullable=True))
    op.alter_column('themes', 'digest_hour',
               existing_type=sa.INTEGER(),
               nullable=False,
               existing_server_default=sa.text('7'))
    op.alter_column('themes', 'digest_enabled',
               existing_type=sa.BOOLEAN(),
               nullable=False,
               existing_server_default=sa.text('true'))
    op.alter_column('themes', 'user_id', nullable=False)
    op.create_foreign_key(None, 'themes', 'users', ['user_id'], ['id'], ondelete='CASCADE')

    op.add_column('webhooks', sa.Column('user_id', sa.UUID(), nullable=True))
    op.alter_column('webhooks', 'user_id', nullable=False)
    op.create_foreign_key(None, 'webhooks', 'users', ['user_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    op.drop_constraint(None, 'webhooks', type_='foreignkey')
    op.drop_column('webhooks', 'user_id')
    op.drop_constraint(None, 'themes', type_='foreignkey')
    op.alter_column('themes', 'digest_enabled',
               existing_type=sa.BOOLEAN(),
               nullable=True,
               existing_server_default=sa.text('true'))
    op.alter_column('themes', 'digest_hour',
               existing_type=sa.INTEGER(),
               nullable=True,
               existing_server_default=sa.text('7'))
    op.drop_column('themes', 'user_id')
    op.alter_column('sources', 'fetch_interval_hours',
               existing_type=sa.INTEGER(),
               nullable=True,
               existing_server_default=sa.text('2'))
    op.drop_constraint(None, 'feedbacks', type_='foreignkey')
    op.drop_column('feedbacks', 'user_id')
    op.drop_table('refresh_tokens')
    op.drop_table('email_verification_tokens')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')