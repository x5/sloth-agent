"""Add tools column to agent_templates

Revision ID: 20260506_agent_tools
Create Date: 2026-05-06

This is a manual migration. Since the project uses SQLAlchemy
Base.metadata.create_all (not Alembic auto-migrate), this file
serves as documentation. To apply manually:

    from backend.app.database import engine, Base
    # Drop and recreate, or:
    # ALTER TABLE agent_templates ADD COLUMN tools VARCHAR(500) DEFAULT '[]';

The "tools" column stores a JSON string array of agent-specific tool names
that supplement the role base tools defined in ROLE_BASE_TOOLS.
"""

# If you need to apply via SQL:
UPGRADE_SQL = """ALTER TABLE agent_templates ADD COLUMN tools VARCHAR(500) NOT NULL DEFAULT '[]';"""
DOWNGRADE_SQL = """ALTER TABLE agent_templates DROP COLUMN tools;"""


def upgrade():
    """Run upgrade migration."""
    import sqlalchemy as sa
    from backend.app.database import sync_engine

    with sync_engine.connect() as conn:
        conn.execute(sa.text(UPGRADE_SQL))
        conn.commit()


def downgrade():
    """Run downgrade migration."""
    import sqlalchemy as sa
    from backend.app.database import sync_engine

    with sync_engine.connect() as conn:
        conn.execute(sa.text(DOWNGRADE_SQL))
        conn.commit()
