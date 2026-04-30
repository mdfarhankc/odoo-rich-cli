from pathlib import Path

MANIFEST = """\
{{
    "name": "{name}",
    "version": "1.0.0",
    "summary": "",
    "description": "",
    "author": "",
    "website": "",
    "category": "Uncategorized",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "views/views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}}
"""

MODELS_PY = """\
from odoo import models, fields, api


class {class_name}(models.Model):
    _name = "{model_name}"
    _description = "{name}"

    name = fields.Char(string="Name", required=True)
"""

VIEWS_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data>

        <!-- {name} views -->

    </data>
</odoo>
"""

CONTROLLERS_PY = """\
# from odoo import http
# from odoo.http import request


# class MyController(http.Controller):
#     @http.route('/my_route', auth='public', type='http')
#     def index(self, **kw):
#         return "Hello, world!"
"""

ACCESS_CSV = "id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink\n"


def create_module(module_name: str, path: str = ".") -> str:
    base = Path(path) / module_name
    if base.exists():
        raise FileExistsError(f"Directory '{base}' already exists.")

    for sub in ("models", "views", "security", "controllers", "static/description"):
        (base / sub).mkdir(parents=True, exist_ok=True)

    files = {
        "__manifest__.py": MANIFEST.format(name=module_name),
        "__init__.py": "from . import models\nfrom . import controllers\n",
        "models/__init__.py": "from . import models\n",
        "models/models.py": MODELS_PY.format(
            class_name=_class_name(module_name),
            model_name=module_name.replace("_", "."),
            name=module_name,
        ),
        "views/views.xml": VIEWS_XML.format(name=module_name),
        "security/ir.model.access.csv": ACCESS_CSV,
        "controllers/__init__.py": "from . import controllers\n",
        "controllers/controllers.py": CONTROLLERS_PY,
        "static/description/.gitkeep": "",
    }
    for relpath, content in files.items():
        (base / relpath).write_text(content, encoding="utf-8")

    return str(base)


def _class_name(module_name: str) -> str:
    return "".join(part.capitalize() for part in module_name.split("_"))
