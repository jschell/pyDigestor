"""Initial SQLite schema with FTS5 and sqlite-vec support

Revision ID: 002
Revises:
Create Date: 2026-01-07 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Text

# revision identifiers, used by Alembic.
revision = '002'
down_revision = None  # This is the initial migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create SQLite schema with FTS5 and vec0 virtual tables."""

    # Create articles table with SQLite-compatible schema
    op.create_table(
        'articles',
        sa.Column('id', Text, nullable=False),
        sa.Column('source_id', Text, nullable=False),
        sa.Column('url', Text, nullable=False),
        sa.Column('title', Text, nullable=False),
        sa.Column('content', Text, nullable=True),
        sa.Column('summary', Text, nullable=True),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('fetched_at', sa.DateTime(), nullable=False),
        sa.Column('status', Text, nullable=False),
        sa.Column('meta', Text, nullable=False),  # JSON as TEXT
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_articles_source_id', 'articles', ['source_id'], unique=True)
    op.create_index('ix_articles_status', 'articles', ['status'], unique=False)
    op.create_index('ix_articles_fetched_at', 'articles', ['fetched_at'], unique=False)

    # Create triage_decisions table
    op.create_table(
        'triage_decisions',
        sa.Column('id', Text, nullable=False),
        sa.Column('article_id', Text, nullable=False),
        sa.Column('keep', sa.Boolean(), nullable=False),
        sa.Column('reasoning', Text, nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_triage_decisions_article_id', 'triage_decisions', ['article_id'], unique=False)

    # Create signals table
    op.create_table(
        'signals',
        sa.Column('id', Text, nullable=False),
        sa.Column('article_id', Text, nullable=False),
        sa.Column('signal_type', Text, nullable=False),
        sa.Column('content', Text, nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('meta', Text, nullable=False),  # JSON as TEXT
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_signals_article_id', 'signals', ['article_id'], unique=False)
    op.create_index('ix_signals_signal_type', 'signals', ['signal_type'], unique=False)
    op.create_index('ix_signals_created_at', 'signals', ['created_at'], unique=False)

    # Create FTS5 virtual table for full-text search
    op.execute("""
        CREATE VIRTUAL TABLE articles_fts USING fts5(
            article_id UNINDEXED,
            title,
            content,
            summary,
            content='',
            tokenize='porter unicode61'
        );
    """)

    # Create triggers to keep FTS5 in sync with articles table
    op.execute("""
        CREATE TRIGGER articles_fts_insert AFTER INSERT ON articles
        BEGIN
            INSERT INTO articles_fts(article_id, title, content, summary)
            VALUES (
                new.id,
                new.title,
                COALESCE(new.content, ''),
                COALESCE(new.summary, '')
            );
        END;
    """)

    op.execute("""
        CREATE TRIGGER articles_fts_update AFTER UPDATE ON articles
        BEGIN
            DELETE FROM articles_fts WHERE article_id = old.id;
            INSERT INTO articles_fts(article_id, title, content, summary)
            VALUES (
                new.id,
                new.title,
                COALESCE(new.content, ''),
                COALESCE(new.summary, '')
            );
        END;
    """)

    op.execute("""
        CREATE TRIGGER articles_fts_delete AFTER DELETE ON articles
        BEGIN
            DELETE FROM articles_fts WHERE article_id = old.id;
        END;
    """)


def downgrade() -> None:
    """Downgrade not supported for clean slate migration."""
    raise NotImplementedError("Downgrade not supported for clean slate migration from PostgreSQL to SQLite")
