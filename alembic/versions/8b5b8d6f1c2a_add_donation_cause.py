"""Add benefit scopes and policies

Revision ID: 8b5b8d6f1c2a
Revises: 1fafdb893dd5

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8b5b8d6f1c2a"
down_revision: Union[str, None] = "1fafdb893dd5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.rename_table("donation", "benefit_grant")
    op.create_table(
        "benefits_scope",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("name"),
    )
    op.bulk_insert(
        sa.table(
            "benefits_scope",
            sa.column("name", sa.String()),
            sa.column("active", sa.Boolean()),
        ),
        [
            {"name": "*", "active": False},
            {"name": "legacy", "active": False},
            {"name": "paradise", "active": True},
            {"name": "bandastation", "active": True},
            {"name": "bandamarines", "active": True},
        ],
    )
    op.add_column("benefit_grant", sa.Column("cause", sa.String(length=255), nullable=True))
    op.add_column("benefit_grant", sa.Column("scope", sa.String(length=255), nullable=True))
    op.execute(sa.text("UPDATE benefit_grant SET cause = CONCAT('donor_t', tier, '@ss220'), scope = 'legacy'"))
    op.alter_column("benefit_grant", "scope", existing_type=sa.String(length=255), nullable=False)
    op.create_foreign_key(
        "fk_benefit_grant_scope",
        "benefit_grant",
        "benefits_scope",
        ["scope"],
        ["name"],
    )
    op.create_check_constraint("ck_benefit_grant_scope_not_default", "benefit_grant", "scope <> '*'")
    op.create_table(
        "benefit_policy",
        sa.Column("cause", sa.String(length=255), nullable=False),
        sa.Column("scope", sa.String(length=255), nullable=False, server_default=sa.text("'*'")),
        sa.Column("benefit_tier", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["scope"], ["benefits_scope.name"]),
        sa.PrimaryKeyConstraint("cause", "scope"),
    )
    op.bulk_insert(
        sa.table(
            "benefit_policy",
            sa.column("cause", sa.String()),
            sa.column("benefit_tier", sa.Integer()),
            sa.column("active", sa.Boolean()),
        ),
        [
            {"cause": "developer@discord", "benefit_tier": 5, "active": True},
            {"cause": "banda@ss220", "benefit_tier": 5, "active": True},
            {"cause": "lead_moderator@discord", "benefit_tier": 5, "active": True},
            {"cause": "lead_administrator@prime", "benefit_tier": 5, "active": True},
            {"cause": "lead_administrator@paradise", "benefit_tier": 5, "active": True},
            {"cause": "lead_administrator@ss14", "benefit_tier": 5, "active": True},
            {"cause": "lead_administrator@bandastation", "benefit_tier": 5, "active": True},
            {"cause": "lead_administrator@bandamarines", "benefit_tier": 5, "active": True},
            {"cause": "lead_administrator@exodus", "benefit_tier": 5, "active": True},
            {"cause": "project_manager@paradise", "benefit_tier": 5, "active": True},
            {"cause": "project_manager@ss14", "benefit_tier": 5, "active": True},
            {"cause": "project_manager@bandastation", "benefit_tier": 5, "active": True},
            {"cause": "project_manager@bandamarines", "benefit_tier": 5, "active": True},
            {"cause": "project_manager@exodus", "benefit_tier": 5, "active": True},
            {"cause": "lead_developer@paradise", "benefit_tier": 5, "active": True},
            {"cause": "lead_developer@ss14", "benefit_tier": 5, "active": True},
            {"cause": "lead_developer@bandastation", "benefit_tier": 5, "active": True},
            {"cause": "lead_developer@bandamarines", "benefit_tier": 5, "active": True},
            {"cause": "lead_developer@exodus", "benefit_tier": 5, "active": True},
            {"cause": "maintainer@ss220", "benefit_tier": 5, "active": True},
            {"cause": "lead_wiki_editor@paradise", "benefit_tier": 5, "active": True},
            {"cause": "lead_wiki_editor@ss14", "benefit_tier": 5, "active": True},
            {"cause": "lead_wiki_editor@bandastation", "benefit_tier": 5, "active": True},
            {"cause": "lead_wiki_editor@bandamarines", "benefit_tier": 5, "active": True},
            {"cause": "lead_wiki_editor@exodus", "benefit_tier": 5, "active": True},
            {"cause": "moderator@discord", "benefit_tier": 3, "active": True},
            {"cause": "maintainer@paradise", "benefit_tier": 4, "active": True},
            {"cause": "maintainer@ss14", "benefit_tier": 4, "active": True},
            {"cause": "maintainer@bandastation", "benefit_tier": 4, "active": True},
            {"cause": "maintainer@bandamarines", "benefit_tier": 4, "active": True},
            {"cause": "maintainer@exodus", "benefit_tier": 4, "active": True},
            {"cause": "administrator@prime", "benefit_tier": 3, "active": True},
            {"cause": "administrator@paradise", "benefit_tier": 3, "active": True},
            {"cause": "administrator@ss14", "benefit_tier": 3, "active": True},
            {"cause": "administrator@bandastation", "benefit_tier": 3, "active": True},
            {"cause": "administrator@bandamarines", "benefit_tier": 3, "active": True},
            {"cause": "administrator@exodus", "benefit_tier": 3, "active": True},
            {"cause": "trainee_administrator@paradise", "benefit_tier": 2, "active": True},
            {"cause": "trainee_administrator@ss14", "benefit_tier": 2, "active": True},
            {"cause": "trainee_administrator@bandastation", "benefit_tier": 2, "active": True},
            {"cause": "trainee_administrator@bandamarines", "benefit_tier": 2, "active": True},
            {"cause": "trainee_administrator@exodus", "benefit_tier": 2, "active": True},
            {"cause": "mentor@prime", "benefit_tier": 1, "active": True},
            {"cause": "mentor@paradise", "benefit_tier": 1, "active": True},
            {"cause": "mentor@ss14", "benefit_tier": 1, "active": True},
            {"cause": "mentor@bandastation", "benefit_tier": 1, "active": True},
            {"cause": "mentor@bandamarines", "benefit_tier": 1, "active": True},
            {"cause": "mentor@exodus", "benefit_tier": 1, "active": True},
            {"cause": "prototyper@ss14", "benefit_tier": 2, "active": True},
            {"cause": "game_designer@ss14", "benefit_tier": 3, "active": True},
            {"cause": "game_designer@exodus", "benefit_tier": 3, "active": True},
            {"cause": "donor_t5@ss220", "benefit_tier": 5, "active": True},
            {"cause": "donor_t4@ss220", "benefit_tier": 4, "active": True},
            {"cause": "donor_t3@ss220", "benefit_tier": 3, "active": True},
            {"cause": "donor_t2@ss220", "benefit_tier": 2, "active": True},
            {"cause": "donor_t1@ss220", "benefit_tier": 1, "active": True},
            {"cause": "booster@discord", "benefit_tier": 2, "active": True},
        ],
    )


def downgrade() -> None:
    op.drop_constraint("fk_benefit_grant_scope", "benefit_grant", type_="foreignkey")
    op.drop_constraint("ck_benefit_grant_scope_not_default", "benefit_grant", type_="check")
    op.drop_column("benefit_grant", "scope")
    op.drop_column("benefit_grant", "cause")
    op.drop_table("benefit_policy")
    op.drop_table("benefits_scope")
    op.rename_table("benefit_grant", "donation")
