"""Alembic script mako template.

This is the template used by `alembic revision` to generate new
revision files. Any substitutions defined in the `[alembic]` section
of `alembic.ini` will be applied to this file.

This template is for use with Alembic 1.x.

"""
from alembic.autogenerate import renderers
from alembic.operations import ops
from alembic.runtime import migration
from alembic.util import editor, rev_id, template

revision_context = {
    "imports": set(),
    "autogen_context": {"opts": {"sqlalchemy_module_prefix": "sa."}},
}

${'\\n'.join(imports) or ''}

# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade():
${render_upgrade_instructions(upgrades)}


def downgrade():
${render_downgrade_instructions(downgrades)} 