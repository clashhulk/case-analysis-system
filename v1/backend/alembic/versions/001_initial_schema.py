"""initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # Create events table (event store)
    op.create_table(
        'events',
        sa.Column('event_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('aggregate_type', sa.String(50), nullable=False),
        sa.Column('aggregate_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('event_data', postgresql.JSONB, nullable=False),
        sa.Column('event_metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('sequence_number', sa.BigInteger, primary_key=True, autoincrement=True)
    )

    # Indexes for events
    op.create_index('idx_events_aggregate', 'events', ['aggregate_type', 'aggregate_id'])
    op.create_index('idx_events_created_at', 'events', ['created_at'], postgresql_using='btree')

    # Create cases table (read model)
    op.create_table(
        'cases',
        sa.Column('case_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('case_number', sa.String(100), nullable=False, unique=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('case_metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now())
    )

    # Index for case_number lookups
    op.create_index('idx_cases_case_number', 'cases', ['case_number'], unique=True)


def downgrade() -> None:
    op.drop_index('idx_cases_case_number', table_name='cases')
    op.drop_table('cases')
    op.drop_index('idx_events_created_at', table_name='events')
    op.drop_index('idx_events_aggregate', table_name='events')
    op.drop_table('events')
    op.execute('DROP EXTENSION IF EXISTS vector')
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')
