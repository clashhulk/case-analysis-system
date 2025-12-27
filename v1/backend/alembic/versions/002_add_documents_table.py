"""add documents table

Revision ID: 002
Revises: 001
Create Date: 2024-01-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create documents table
    op.create_table(
        'documents',
        sa.Column('document_id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filename', sa.String(500), nullable=False),
        sa.Column('original_filename', sa.String(500), nullable=False),
        sa.Column('file_type', sa.String(100), nullable=False),
        sa.Column('file_size', sa.BigInteger, nullable=False),
        sa.Column('s3_key', sa.String(1000), nullable=False, unique=True),
        sa.Column('s3_bucket', sa.String(255), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='uploaded'),
        sa.Column('document_metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(),
                  onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['case_id'], ['cases.case_id'], ondelete='CASCADE')
    )

    # Indexes for efficient queries
    op.create_index('idx_documents_case_id', 'documents', ['case_id'])
    op.create_index('idx_documents_created_at', 'documents', ['created_at'], postgresql_using='btree')
    op.create_index('idx_documents_status', 'documents', ['status'])


def downgrade() -> None:
    op.drop_index('idx_documents_status', table_name='documents')
    op.drop_index('idx_documents_created_at', table_name='documents')
    op.drop_index('idx_documents_case_id', table_name='documents')
    op.drop_table('documents')
