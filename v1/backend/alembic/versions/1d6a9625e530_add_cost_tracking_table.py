"""Add cost tracking table

Revision ID: 1d6a9625e530
Revises: 002
Create Date: 2026-01-04 01:04:40.849058

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1d6a9625e530'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'ai_cost_tracking',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('document_id', sa.UUID(), nullable=True),
        sa.Column('case_id', sa.UUID(), nullable=True),
        sa.Column('service_type', sa.String(), nullable=False),  # 'text_analysis', 'entity_extraction', 'vision_ai'
        sa.Column('model_name', sa.String(), nullable=False),
        sa.Column('input_tokens', sa.Integer(), nullable=True),
        sa.Column('output_tokens', sa.Integer(), nullable=True),
        sa.Column('cost_usd', sa.Numeric(10, 6), nullable=False),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('extra_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.document_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['case_id'], ['cases.case_id'], ondelete='SET NULL')
    )

    # Create indexes for efficient querying
    op.create_index('idx_ai_cost_tracking_created_at', 'ai_cost_tracking', ['created_at'])
    op.create_index('idx_ai_cost_tracking_service_type', 'ai_cost_tracking', ['service_type'])
    op.create_index('idx_ai_cost_tracking_document_id', 'ai_cost_tracking', ['document_id'])
    op.create_index('idx_ai_cost_tracking_case_id', 'ai_cost_tracking', ['case_id'])


def downgrade() -> None:
    op.drop_index('idx_ai_cost_tracking_case_id')
    op.drop_index('idx_ai_cost_tracking_document_id')
    op.drop_index('idx_ai_cost_tracking_service_type')
    op.drop_index('idx_ai_cost_tracking_created_at')
    op.drop_table('ai_cost_tracking')
