"""Add users table and user_id to subjects

Revision ID: 002
Revises: 001
Create Date: 2026-01-25

This migration:
1. Creates the users table
2. Adds user_id foreign key to subjects
3. For existing data, we need to either delete it or create a default user

Note: Since this is a breaking change (existing subjects won't have a user),
for a fresh install this works fine. For existing data, you'd need to:
- Create a migration user
- Assign existing subjects to that user
- Or simply delete existing data (acceptable for dev/early stage)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add users table and user_id to subjects."""
    
    # 1. Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column(
            'created_at', 
            sa.DateTime(), 
            nullable=False, 
            server_default=sa.text('CURRENT_TIMESTAMP')
        ),
        sa.Column(
            'updated_at', 
            sa.DateTime(), 
            nullable=False, 
            server_default=sa.text('CURRENT_TIMESTAMP')
        ),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
    )
    
    # Create index on email for fast lookups
    op.create_index('ix_users_email', 'users', ['email'])
    
    # 2. For SQLite, we need to recreate the subjects table to add the foreign key
    # Using batch mode for SQLite compatibility
    
    with op.batch_alter_table('subjects', schema=None) as batch_op:
        # Drop the old unique constraint on name (now unique per user, not globally)
        batch_op.drop_constraint('uq_subjects_name', type_='unique')
        
        # Add user_id column (nullable initially for migration)
        batch_op.add_column(
            sa.Column('user_id', sa.String(36), nullable=True)
        )
    
    # 3. Delete any existing subjects (they have no user)
    # In production with existing data, you'd create a migration user instead
    op.execute("DELETE FROM subjects")
    
    # 4. Now make user_id NOT NULL and add foreign key
    with op.batch_alter_table('subjects', schema=None) as batch_op:
        # Make user_id NOT NULL
        batch_op.alter_column('user_id', nullable=False)
        
        # Add foreign key constraint
        batch_op.create_foreign_key(
            'fk_subjects_user_id',
            'users',
            ['user_id'],
            ['id'],
            ondelete='CASCADE'
        )
        
        # Add index for user_id queries
        batch_op.create_index('ix_subjects_user_id', ['user_id'])
        
        # Add composite index for user_id + name
        batch_op.create_index('ix_subjects_user_id_name', ['user_id', 'name'])


def downgrade() -> None:
    """Remove users table and user_id from subjects."""
    
    # 1. Remove foreign key and user_id from subjects
    with op.batch_alter_table('subjects', schema=None) as batch_op:
        batch_op.drop_index('ix_subjects_user_id_name')
        batch_op.drop_index('ix_subjects_user_id')
        batch_op.drop_constraint('fk_subjects_user_id', type_='foreignkey')
        batch_op.drop_column('user_id')
        
        # Restore global unique constraint on name
        batch_op.create_unique_constraint('uq_subjects_name', ['name'])
    
    # 2. Drop users table
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
