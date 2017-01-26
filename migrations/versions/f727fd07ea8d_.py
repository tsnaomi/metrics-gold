"""empty message

Revision ID: f727fd07ea8d
Revises: 4862fb803e10
Create Date: 2017-01-25 21:21:24.156803

"""

# revision identifiers, used by Alembic.
revision = 'f727fd07ea8d'
down_revision = '4862fb803e10'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('Token', sa.Column('corpus_inform_2', sa.Float(), nullable=True))
    op.add_column('Token', sa.Column('corpus_inform_3', sa.Float(), nullable=True))
    op.add_column('Token', sa.Column('corpus_posterior_1', sa.Float(), nullable=True))
    op.add_column('Token', sa.Column('corpus_posterior_2', sa.Float(), nullable=True))
    op.add_column('Token', sa.Column('corpus_posterior_3', sa.Float(), nullable=True))
    op.add_column('Token', sa.Column('doc_inform_2', sa.Float(), nullable=True))
    op.add_column('Token', sa.Column('doc_inform_3', sa.Float(), nullable=True))
    op.add_column('Token', sa.Column('doc_posterior_1', sa.Float(), nullable=True))
    op.add_column('Token', sa.Column('doc_posterior_2', sa.Float(), nullable=True))
    op.add_column('Token', sa.Column('doc_posterior_3', sa.Float(), nullable=True))
    op.add_column('User', sa.Column('email', sa.String(), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('Token', 'doc_posterior_3')
    op.drop_column('Token', 'doc_posterior_2')
    op.drop_column('Token', 'doc_posterior_1')
    op.drop_column('Token', 'doc_inform_3')
    op.drop_column('Token', 'doc_inform_2')
    op.drop_column('Token', 'corpus_posterior_3')
    op.drop_column('Token', 'corpus_posterior_2')
    op.drop_column('Token', 'corpus_posterior_1')
    op.drop_column('Token', 'corpus_inform_3')
    op.drop_column('Token', 'corpus_inform_2')
    op.drop_column('User', 'email')
    ### end Alembic commands ###