"""initial_schema

Revision ID: c8d44668e193
Revises:
Create Date: 2026-02-07 19:31:55.006012

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8d44668e193'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all application tables."""
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
    )

    op.create_table(
        'profiles',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), unique=True, nullable=False),
        sa.Column('skills', sa.JSON, nullable=False),
        sa.Column('experience_years', sa.Integer, nullable=True),
        sa.Column('job_titles', sa.JSON, nullable=False),
        sa.Column('summary', sa.Text, nullable=False, server_default=''),
        sa.Column('cv_text', sa.Text, nullable=False, server_default=''),
        sa.Column('uploaded_at', sa.DateTime, nullable=False),
    )

    op.create_table(
        'preferences',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), unique=True, nullable=False),
        sa.Column('location_type', sa.String(20), nullable=False, server_default='any'),
        sa.Column('target_roles', sa.JSON, nullable=False),
        sa.Column('excluded_companies', sa.JSON, nullable=False),
        sa.Column('min_salary', sa.Integer, nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )

    op.create_table(
        'search_sessions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('queries', sa.JSON, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('completed_at', sa.DateTime, nullable=True),
    )

    op.create_table(
        'job_results',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('search_id', sa.String(36), sa.ForeignKey('search_sessions.id'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('company', sa.String(255), nullable=False),
        sa.Column('match_score', sa.Float, nullable=False),
        sa.Column('match_reason', sa.Text, nullable=False),
        sa.Column('location_type', sa.String(20), nullable=False, server_default='unknown'),
        sa.Column('salary', sa.String(100), nullable=True),
        sa.Column('posting_url', sa.Text, nullable=False),
        sa.Column('description_snippet', sa.Text, nullable=False, server_default=''),
    )

    op.create_table(
        'chat_sessions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('thread_id', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )

    op.create_table(
        'chat_messages',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('session_id', sa.String(36), sa.ForeignKey('chat_sessions.id'), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('message_type', sa.String(20), nullable=False, server_default='text'),
        sa.Column('extra_data', sa.JSON, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
    )

    op.create_table(
        'bookmarks',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('session_id', sa.String(36), nullable=False, index=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('company', sa.String(255), nullable=False),
        sa.Column('match_score', sa.Float, nullable=False, server_default='0.0'),
        sa.Column('match_reason', sa.Text, nullable=False, server_default=''),
        sa.Column('location_type', sa.String(20), nullable=False, server_default='unknown'),
        sa.Column('salary', sa.String(100), nullable=True),
        sa.Column('posting_url', sa.Text, nullable=False),
        sa.Column('description_snippet', sa.Text, nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime, nullable=False),
    )


def downgrade() -> None:
    """Drop all application tables."""
    op.drop_table('bookmarks')
    op.drop_table('chat_messages')
    op.drop_table('chat_sessions')
    op.drop_table('job_results')
    op.drop_table('search_sessions')
    op.drop_table('preferences')
    op.drop_table('profiles')
    op.drop_table('users')
