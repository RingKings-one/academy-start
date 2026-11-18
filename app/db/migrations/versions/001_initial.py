"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-11-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # directions
    op.create_table(
        "directions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("age_min", sa.Integer(), nullable=True),
        sa.Column("age_max", sa.Integer(), nullable=True),
        sa.Column("icon_url", sa.String(length=512), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    # users (без FK на children пока — добавим позже)
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("first_name", sa.String(length=128), nullable=True),
        sa.Column("username", sa.String(length=128), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("state", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("active_child_id", sa.BigInteger(), nullable=True),
        sa.Column("bot_blocked", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_id"),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"])

    # children
    op.create_table(
        "children",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("parent_user_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["parent_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_children_parent_user_id", "children", ["parent_user_id"])

    # теперь FK active_child_id
    op.create_foreign_key(
        "fk_users_active_child",
        "users",
        "children",
        ["active_child_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # coach_profiles
    op.create_table(
        "coach_profiles",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("photo_url", sa.String(length=512), nullable=True),
        sa.Column("achievements", sa.Text(), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_published", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    # groups
    op.create_table(
        "groups",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("direction_id", sa.BigInteger(), nullable=False),
        sa.Column("coach_user_id", sa.BigInteger(), nullable=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("age_min", sa.Integer(), nullable=True),
        sa.Column("age_max", sa.Integer(), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("branch", sa.String(length=128), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.ForeignKeyConstraint(["coach_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["direction_id"], ["directions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_groups_direction_id", "groups", ["direction_id"])
    op.create_index("ix_groups_coach_user_id", "groups", ["coach_user_id"])

    # schedule_instances
    op.create_table(
        "schedule_instances",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("group_id", sa.BigInteger(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="scheduled", nullable=False),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("moved_to_instance_id", sa.BigInteger(), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
        sa.ForeignKeyConstraint(["moved_to_instance_id"], ["schedule_instances.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_schedule_instances_group_id", "schedule_instances", ["group_id"])
    op.create_index("ix_schedule_instances_starts_at", "schedule_instances", ["starts_at"])

    # applications
    op.create_table(
        "applications",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("parent_user_id", sa.BigInteger(), nullable=True),
        sa.Column("child_id", sa.BigInteger(), nullable=True),
        sa.Column("child_name", sa.String(length=128), nullable=False),
        sa.Column("child_birth_date", sa.Date(), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("direction_id", sa.BigInteger(), nullable=False),
        sa.Column("group_id", sa.BigInteger(), nullable=True),
        sa.Column("trial_instance_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="new", nullable=False),
        sa.Column("source", sa.String(length=10), nullable=False),
        sa.Column("medcert", sa.String(length=20), nullable=True),
        sa.Column("pd_consent", sa.Boolean(), nullable=False),
        sa.Column("deep_link_token", sa.String(length=64), nullable=True),
        sa.Column("followup_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("noshow_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["child_id"], ["children.id"]),
        sa.ForeignKeyConstraint(["direction_id"], ["directions.id"]),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
        sa.ForeignKeyConstraint(["parent_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["trial_instance_id"], ["schedule_instances.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("deep_link_token"),
    )
    op.create_index("ix_applications_parent_user_id", "applications", ["parent_user_id"])
    op.create_index("ix_applications_status", "applications", ["status"])

    # enrollments
    op.create_table(
        "enrollments",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("child_id", sa.BigInteger(), nullable=False),
        sa.Column("group_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="trial", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["child_id"], ["children.id"]),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # attendance
    op.create_table(
        "attendance",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("child_id", sa.BigInteger(), nullable=False),
        sa.Column("instance_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("source", sa.String(length=10), nullable=False),
        sa.Column("set_by_user_id", sa.BigInteger(), nullable=True),
        sa.Column("set_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["child_id"], ["children.id"]),
        sa.ForeignKeyConstraint(["instance_id"], ["schedule_instances.id"]),
        sa.ForeignKeyConstraint(["set_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("child_id", "instance_id", name="uq_attendance_child_instance"),
    )

    # reminders
    op.create_table(
        "reminders",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("target_user_id", sa.BigInteger(), nullable=False),
        sa.Column("type", sa.String(length=30), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("send_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index("ix_reminders_status_send_at", "reminders", ["status", "send_at"])

    # payments
    op.create_table(
        "payments",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("enrollment_id", sa.BigInteger(), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("period_from", sa.Date(), nullable=False),
        sa.Column("period_to", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["enrollment_id"], ["enrollments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("payments")
    op.drop_table("reminders")
    op.drop_table("attendance")
    op.drop_table("enrollments")
    op.drop_table("applications")
    op.drop_table("schedule_instances")
    op.drop_table("groups")
    op.drop_table("coach_profiles")
    op.drop_constraint("fk_users_active_child", "users", type_="foreignkey")
    op.drop_table("children")
    op.drop_table("users")
    op.drop_table("directions")
