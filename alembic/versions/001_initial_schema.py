"""Initial schema with articles, triage_decisions, and signals tables

Revision ID: 001
Revises:
Create Date: 2026-01-05 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create articles table
    op.create_table(
        'articles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('url', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('title', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('content', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('summary', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('fetched_at', sa.DateTime(), nullable=False),
        sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('meta', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_id')
    )
    op.create_index(op.f('ix_articles_source_id'), 'articles', ['source_id'], unique=False)
    op.create_index('ix_articles_meta', 'articles', ['meta'], postgresql_using='gin')

    # Create triage_decisions table
    op.create_table(
        'triage_decisions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('article_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('keep', sa.Boolean(), nullable=False),
        sa.Column('reasoning', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_triage_decisions_article_id'), 'triage_decisions', ['article_id'], unique=False)

    # Create signals table
    op.create_table(
        'signals',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('article_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('signal_type', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('content', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('meta', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_signals_article_id'), 'signals', ['article_id'], unique=False)
    op.create_index(op.f('ix_signals_signal_type'), 'signals', ['signal_type'], unique=False)
    op.create_index(op.f('ix_signals_created_at'), 'signals', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_table('signals')
    op.drop_table('triage_decisions')
    op.drop_table('articles')
