"""Index on timestamps

Revision ID: 243385d2034
Revises: 235df5f94f20
Create Date: 2014-12-15 09:44:47.556192

"""

# revision identifiers, used by Alembic.
revision = '243385d2034'
down_revision = '235df5f94f20'

from alembic import op
import sqlalchemy as sa


def upgrade():
  op.create_index("created_at_idx", "twitter_tweets", ["created_at"])
  op.create_index("agg_ts_idx", "twitter_tweet_samples", ["agg_ts"])


def downgrade():
  raise NotImplementedError("Rollback is not supported.")
