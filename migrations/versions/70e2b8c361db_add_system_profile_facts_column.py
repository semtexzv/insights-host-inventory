"""empty message

Revision ID: 70e2b8c361db
Revises: 39e75256800b
Create Date: 2019-03-12 09:21:52.037329

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '70e2b8c361db'
down_revision = '39e75256800b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('hosts', sa.Column('system_profile_facts', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('hosts', 'system_profile_facts')
    # ### end Alembic commands ###