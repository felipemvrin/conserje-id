"""Initial migration: create all tables

Revision ID: 001_initial
Revises:
Create Date: 2026-08-25 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial tables: departamentos, residentes, conserjes, visitas."""
    # Create departamentos table
    op.create_table(
        "departamentos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("numero", sa.String(20), nullable=False),
        sa.Column("piso", sa.Integer(), nullable=False),
        sa.Column("descripcion", sa.String(500), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "creado_en", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create residentes table
    op.create_table(
        "residentes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nombre_completo", sa.String(150), nullable=False),
        sa.Column("run", sa.String(12), nullable=False, unique=True),
        sa.Column("telefono", sa.String(20), nullable=True),
        sa.Column("email", sa.String(150), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "creado_en", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column("departamento_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["departamento_id"], ["departamentos.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create conserjes table
    op.create_table(
        "conserjes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(150), nullable=False),
        sa.Column("rut", sa.String(12), nullable=False, unique=True),
        sa.Column("email", sa.String(150), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "creado_en", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create visitas table
    op.create_table(
        "visitas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_visitante", sa.String(12), nullable=False),
        sa.Column("nombre_visitante", sa.String(150), nullable=False),
        sa.Column("fecha_nacimiento_visitante", sa.String(10), nullable=False),
        sa.Column("foto_visitante", sa.LargeBinary(), nullable=True),
        sa.Column("motivo", sa.String(255), nullable=False),
        sa.Column(
            "timestamp_ingreso", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column("timestamp_salida", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notas", sa.String(500), nullable=True),
        sa.Column(
            "creado_en", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column("departamento_id", sa.Integer(), nullable=False),
        sa.Column("residente_destino_id", sa.Integer(), nullable=False),
        sa.Column("conserje_registrador_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["departamento_id"], ["departamentos.id"]),
        sa.ForeignKeyConstraint(["residente_destino_id"], ["residentes.id"]),
        sa.ForeignKeyConstraint(["conserje_registrador_id"], ["conserjes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Drop all tables in reverse order."""
    op.drop_table("visitas")
    op.drop_table("conserjes")
    op.drop_table("residentes")
    op.drop_table("departamentos")
