"""Initial schema

Revision ID: 001_initial_schema
Revises:
Create Date: 2024-12-01 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=True),
        sa.Column('oauth_provider', sa.String(length=50), nullable=True),
        sa.Column('oauth_id', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("oauth_provider IS NULL OR oauth_provider IN ('GOOGLE')", name='check_oauth_provider'),
        sa.PrimaryKeyConstraint('user_id'),
        sa.UniqueConstraint('email')
    )
    op.create_index(op.f('ix_users_user_id'), 'users', ['user_id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=False)
    op.create_index('ix_users_oauth_provider_id', 'users', ['oauth_provider', 'oauth_id'], unique=True)

    # Create bots table (CLEAN - no platform-specific fields)
    op.create_table(
        'bots',
        sa.Column('bot_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('owner_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=96), nullable=False),
        sa.Column('description', sa.String(length=512), nullable=True),
        sa.Column('webhook_secret', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='ACTIVE'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name='check_bot_status'),
        sa.ForeignKeyConstraint(['owner_user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('bot_id'),
        sa.UniqueConstraint('name', 'owner_user_id', name='unique_bot_name_per_user')
    )
    op.create_index(op.f('ix_bots_bot_id'), 'bots', ['bot_id'], unique=False)
    op.create_index(op.f('ix_bots_owner_user_id'), 'bots', ['owner_user_id'], unique=False)
    op.create_index(op.f('ix_bots_status'), 'bots', ['status'], unique=False)
    op.create_index(op.f('ix_bots_updated_at'), 'bots', ['updated_at'], unique=False)

    # Create bot_integrations table (NEW - platform-specific data isolated)
    op.create_table(
        'bot_integrations',
        sa.Column('integration_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('bot_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('platform', sa.String(length=50), nullable=False),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='DISCONNECTED'),
        sa.Column('connected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("platform IN ('WHATSAPP', 'TELEGRAM', 'SLACK')", name='check_integration_platform'),
        sa.CheckConstraint("status IN ('CONNECTED', 'DISCONNECTED', 'CONNECTING', 'ERROR')", name='check_integration_status'),
        sa.ForeignKeyConstraint(['bot_id'], ['bots.bot_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('integration_id')
    )
    op.create_index(op.f('ix_bot_integrations_bot_id'), 'bot_integrations', ['bot_id'], unique=False)
    op.create_index(op.f('ix_bot_integrations_platform'), 'bot_integrations', ['platform'], unique=False)
    op.create_index(op.f('ix_bot_integrations_status'), 'bot_integrations', ['status'], unique=False)
    op.create_index('idx_unique_bot_platform', 'bot_integrations', ['bot_id', 'platform'], unique=True)

    # Create flows table
    op.create_table(
        'flows',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=96), nullable=False),
        sa.Column('bot_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('flow_definition', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('trigger_keywords', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['bot_id'], ['bots.bot_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', 'bot_id', name='unique_flow_name_per_bot')
    )
    op.create_index(op.f('ix_flows_id'), 'flows', ['id'], unique=False)
    op.create_index(op.f('ix_flows_name'), 'flows', ['name'], unique=False)
    op.create_index(op.f('ix_flows_bot_id'), 'flows', ['bot_id'], unique=False)
    op.create_index(op.f('ix_flows_updated_at'), 'flows', ['updated_at'], unique=False)
    op.create_index('idx_flows_keywords', 'flows', ['trigger_keywords'], unique=False, postgresql_using='gin')

    # Create sessions table (with selectively encrypted fields)
    # channel_user_id: Plaintext (needed for queries and unique constraint)
    # flow_snapshot, context: Encrypted (contain sensitive data/PII)
    op.create_table(
        'sessions',
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('channel', sa.String(length=50), nullable=False),
        sa.Column('channel_user_id', sa.String(length=255), nullable=False),  # Plaintext for lookups
        sa.Column('bot_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('flow_id', postgresql.UUID(as_uuid=True), nullable=False),
        # ENCRYPTED: flow_snapshot (contains flow definition)
        sa.Column('flow_snapshot', sa.LargeBinary(), nullable=False),
        sa.Column('current_node_id', sa.String(length=96), nullable=False),
        # ENCRYPTED: context (may contain PII from user inputs)
        sa.Column('context', sa.LargeBinary(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='ACTIVE'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('auto_progression_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('validation_attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('message_history', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.CheckConstraint("status IN ('ACTIVE', 'COMPLETED', 'EXPIRED', 'ERROR')", name='check_session_status'),
        sa.ForeignKeyConstraint(['bot_id'], ['bots.bot_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['flow_id'], ['flows.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('session_id')
    )
    op.create_index(op.f('ix_sessions_channel_user_id'), 'sessions', ['channel_user_id'], unique=False)
    op.create_index(op.f('ix_sessions_bot_id'), 'sessions', ['bot_id'], unique=False)
    op.create_index(op.f('ix_sessions_flow_id'), 'sessions', ['flow_id'], unique=False)
    op.create_index(op.f('ix_sessions_status'), 'sessions', ['status'], unique=False)
    op.create_index('idx_unique_active_session', 'sessions', ['channel', 'channel_user_id', 'bot_id'],
                    unique=True, postgresql_where=sa.text("status = 'ACTIVE'"))
    op.create_index('idx_sessions_expires', 'sessions', ['expires_at'],
                    unique=False, postgresql_where=sa.text("status = 'ACTIVE'"))

    # Create audit_logs table (comprehensive security audit trail)
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=True),  # Pre-masked user identifier
        sa.Column('resource_type', sa.String(length=64), nullable=True),
        sa.Column('resource_id', sa.String(length=255), nullable=True),
        sa.Column('action', sa.String(length=128), nullable=False),
        sa.Column('result', sa.String(length=32), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_timestamp'), 'audit_logs', ['timestamp'], unique=False)
    op.create_index(op.f('ix_audit_logs_event_type'), 'audit_logs', ['event_type'], unique=False)
    op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)
    op.create_index('idx_audit_event_timestamp', 'audit_logs', ['event_type', 'timestamp'], unique=False)
    op.create_index('idx_audit_user_timestamp', 'audit_logs', ['user_id', 'timestamp'], unique=False)


def downgrade() -> None:
    # Drop audit_logs table
    op.drop_index('idx_audit_user_timestamp', table_name='audit_logs')
    op.drop_index('idx_audit_event_timestamp', table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_action'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_user_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_event_type'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_timestamp'), table_name='audit_logs')
    op.drop_table('audit_logs')

    # Drop sessions table
    op.drop_index('idx_sessions_expires', table_name='sessions', postgresql_where=sa.text("status = 'ACTIVE'"))
    op.drop_index('idx_unique_active_session', table_name='sessions', postgresql_where=sa.text("status = 'ACTIVE'"))
    op.drop_index(op.f('ix_sessions_status'), table_name='sessions')
    op.drop_index(op.f('ix_sessions_flow_id'), table_name='sessions')
    op.drop_index(op.f('ix_sessions_bot_id'), table_name='sessions')
    op.drop_index(op.f('ix_sessions_channel_user_id'), table_name='sessions')
    op.drop_table('sessions')

    # Drop flows table
    op.drop_index('idx_flows_keywords', table_name='flows', postgresql_using='gin')
    op.drop_index(op.f('ix_flows_updated_at'), table_name='flows')
    op.drop_index(op.f('ix_flows_bot_id'), table_name='flows')
    op.drop_index(op.f('ix_flows_name'), table_name='flows')
    op.drop_index(op.f('ix_flows_id'), table_name='flows')
    op.drop_table('flows')

    # Drop bot_integrations table
    op.drop_index('idx_unique_bot_platform', table_name='bot_integrations')
    op.drop_index(op.f('ix_bot_integrations_status'), table_name='bot_integrations')
    op.drop_index(op.f('ix_bot_integrations_platform'), table_name='bot_integrations')
    op.drop_index(op.f('ix_bot_integrations_bot_id'), table_name='bot_integrations')
    op.drop_table('bot_integrations')

    # Drop bots table
    op.drop_index(op.f('ix_bots_updated_at'), table_name='bots')
    op.drop_index(op.f('ix_bots_status'), table_name='bots')
    op.drop_index(op.f('ix_bots_owner_user_id'), table_name='bots')
    op.drop_index(op.f('ix_bots_bot_id'), table_name='bots')
    op.drop_table('bots')

    # Drop users table
    op.drop_index('ix_users_oauth_provider_id', table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_user_id'), table_name='users')
    op.drop_table('users')
