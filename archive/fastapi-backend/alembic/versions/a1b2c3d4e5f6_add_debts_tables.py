"""add debts and debt payments tables

Revision ID: a1b2c3d4e5f6
Revises: 92093110c13f
Create Date: 2025-11-11 19:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '92093110c13f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create debts table
    op.create_table('debts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('entity_type', sa.String(length=20), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('amount_ngn', sa.Numeric(15, 2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('description', sa.String(length=1000), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('priority', sa.String(length=10), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("type IN ('receivable', 'payable')", name='check_debt_type'),
        sa.CheckConstraint("entity_type IN ('customer', 'supplier', 'other')", name='check_entity_type'),
        sa.CheckConstraint("status IN ('pending', 'partial', 'paid', 'overdue', 'cancelled')", name='check_debt_status'),
        sa.CheckConstraint("priority IN ('low', 'medium', 'high')", name='check_priority'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_debts_entity_type'), 'debts', ['entity_type'], unique=False)
    op.create_index(op.f('ix_debts_entity_id'), 'debts', ['entity_id'], unique=False)
    op.create_index(op.f('ix_debts_status'), 'debts', ['status'], unique=False)
    op.create_index(op.f('ix_debts_due_date'), 'debts', ['due_date'], unique=False)

    # Create debt_payments table
    op.create_table('debt_payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('debt_id', sa.Integer(), nullable=False),
        sa.Column('amount_ngn', sa.Numeric(15, 2), nullable=False),
        sa.Column('payment_date', sa.Date(), nullable=False),
        sa.Column('payment_method', sa.String(length=50), nullable=True),
        sa.Column('notes', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['debt_id'], ['debts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_debt_payments_debt_id'), 'debt_payments', ['debt_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_debt_payments_debt_id'), table_name='debt_payments')
    op.drop_table('debt_payments')
    op.drop_index(op.f('ix_debts_due_date'), table_name='debts')
    op.drop_index(op.f('ix_debts_status'), table_name='debts')
    op.drop_index(op.f('ix_debts_entity_id'), table_name='debts')
    op.drop_index(op.f('ix_debts_entity_type'), table_name='debts')
    op.drop_table('debts')
