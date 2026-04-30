from odoo_rich_cli.config import OdooConfig
from odoo_rich_cli.shell import ShellResult, execute


def _run(config: OdooConfig, script: str, timeout: int = 120) -> ShellResult:
    return execute(script, config.config_path_str, config.db_name, timeout=timeout)


def _module_action_script(name: str, action: str, label: str) -> str:
    return f"""\
module = env["ir.module.module"].search([("name", "=", "{name}")], limit=1)
if not module:
    raise Exception("Module '{name}' not found in the database.")
module.{action}()
env.cr.commit()
_result = {{"ok": True, "message": "Module '{name}' {label} successfully."}}"""


def install_module(config: OdooConfig, module_name: str) -> ShellResult:
    return _run(config, _module_action_script(module_name, "button_immediate_install", "installed"))


def upgrade_module(config: OdooConfig, module_name: str) -> ShellResult:
    return _run(config, _module_action_script(module_name, "button_immediate_upgrade", "upgraded"))


def uninstall_module(config: OdooConfig, module_name: str) -> ShellResult:
    return _run(
        config, _module_action_script(module_name, "button_immediate_uninstall", "uninstalled")
    )


def update_list(config: OdooConfig) -> ShellResult:
    return _run(
        config,
        """\
env["ir.module.module"].update_list()
env.cr.commit()
_result = {"ok": True, "message": "Module list updated successfully."}""",
    )


def module_info(config: OdooConfig, module_name: str) -> ShellResult:
    return _run(
        config,
        f"""\
module = env["ir.module.module"].search([("name", "=", "{module_name}")], limit=1)
if not module:
    raise Exception("Module '{module_name}' not found in the database.")
deps = [d.name for d in module.dependencies_id]
rev_deps = env["ir.module.module.dependency"].search([("name", "=", module.name)])
_result = {{
    "ok": True,
    "message": "Module info retrieved.",
    "data": {{
        "name": module.shortdesc or module.name,
        "technical_name": module.name,
        "state": module.state,
        "version": module.installed_version or module.latest_version or "",
        "author": module.author or "",
        "summary": module.summary or "",
        "dependencies": deps,
        "reverse_dependencies": [d.module_id.name for d in rev_deps],
    }},
}}""",
    )


def list_modules(config: OdooConfig, state_filter: str = "all") -> ShellResult:
    domain = {
        "installed": '[("state", "=", "installed")]',
        "uninstalled": '[("state", "=", "uninstalled")]',
    }.get(state_filter, "[]")

    return _run(
        config,
        f"""\
modules = env["ir.module.module"].search({domain}, order="name")
_result = {{
    "ok": True,
    "message": str(len(modules)) + " module(s) found.",
    "data": [
        {{
            "name": m.shortdesc or m.name,
            "technical_name": m.name,
            "state": m.state,
            "version": m.installed_version or m.latest_version or "",
        }}
        for m in modules
    ],
}}""",
        timeout=180,
    )


def clear_assets(config: OdooConfig) -> ShellResult:
    return _run(
        config,
        """\
assets = env["ir.attachment"].search([
    ("name", "like", ".assets_"),
    ("res_model", "=", "ir.ui.view"),
])
count = len(assets)
if count:
    assets.unlink()
    env.cr.commit()
_result = {"ok": True, "message": str(count) + " asset(s) deleted."}""",
    )


def reset_password(config: OdooConfig, user: str = "admin", password: str = "admin") -> ShellResult:
    # Escape backslash first, then single quote — order matters.
    safe_user = user.replace("\\", "\\\\").replace("'", "\\'")
    safe_pass = password.replace("\\", "\\\\").replace("'", "\\'")
    return _run(
        config,
        f"""\
user_rec = env["res.users"].search([("login", "=", '{safe_user}')], limit=1)
if not user_rec:
    raise Exception("User '{safe_user}' not found.")
user_rec.password = '{safe_pass}'
env.cr.commit()
_result = {{"ok": True, "message": "Password for '{safe_user}' reset successfully."}}""",
    )


def shell_exec(config: OdooConfig, script_content: str) -> ShellResult:
    return _run(config, script_content, timeout=300)


def cron_list(config: OdooConfig) -> ShellResult:
    return _run(
        config,
        """\
crons = env["ir.cron"].sudo().search([], order="name")
_result = {
    "ok": True,
    "message": str(len(crons)) + " scheduled action(s) found.",
    "data": [
        {
            "id": c.id,
            "name": c.name,
            "active": c.active,
            "interval_number": c.interval_number,
            "interval_type": c.interval_type,
            "model": c.model_id.model if c.model_id else "",
            "user": c.user_id.login if c.user_id else "",
        }
        for c in crons
    ],
}""",
    )


def cron_toggle(config: OdooConfig, cron_id: int) -> ShellResult:
    return _run(
        config,
        f"""\
cron = env["ir.cron"].sudo().browse({cron_id})
if not cron.exists():
    raise Exception("Scheduled action with ID {cron_id} not found.")
cron.active = not cron.active
env.cr.commit()
new_state = "enabled" if cron.active else "disabled"
_result = {{"ok": True, "message": "'" + cron.name + "' " + new_state + "."}}""",
    )


def cron_disable_all(config: OdooConfig) -> ShellResult:
    return _run(
        config,
        """\
crons = env["ir.cron"].sudo().search([("active", "=", True)])
count = len(crons)
if count:
    crons.write({"active": False})
    env.cr.commit()
_result = {"ok": True, "message": str(count) + " scheduled action(s) disabled."}""",
    )


def cron_enable_all(config: OdooConfig) -> ShellResult:
    return _run(
        config,
        """\
crons = env["ir.cron"].sudo().search([("active", "=", False)])
count = len(crons)
if count:
    crons.write({"active": True})
    env.cr.commit()
_result = {"ok": True, "message": str(count) + " scheduled action(s) enabled."}""",
    )


# Database operations call into odoo.service.db.* — these run against the connected
# DB but operate on a target DB given as argument. Trying to operate on the connected
# DB itself (e.g. dropping it) will fail; pick a different connection via -d.


def db_list(config: OdooConfig) -> ShellResult:
    return _run(
        config,
        """\
from odoo.service import db as _db
dbs = _db.list_dbs(force=True)
_result = {
    "ok": True,
    "message": str(len(dbs)) + " database(s) found.",
    "data": dbs,
}""",
    )


def db_drop(config: OdooConfig, db_name: str) -> ShellResult:
    return _run(
        config,
        f"""\
from odoo.service import db as _db
target = "{db_name}"
if target == env.cr.dbname:
    raise Exception("Refusing to drop the connected database '" + target + "'. Use -d to point orc at a different database first.")
if not _db.exp_db_exist(target):
    raise Exception("Database '" + target + "' does not exist.")
_db.exp_drop(target)
_result = {{"ok": True, "message": "Database '" + target + "' dropped."}}""",
    )


def db_backup(config: OdooConfig, db_name: str, output_path: str) -> ShellResult:
    return _run(
        config,
        f"""\
from odoo.service import db as _db
target = "{db_name}"
output = {output_path!r}
if not _db.exp_db_exist(target):
    raise Exception("Database '" + target + "' does not exist.")
with open(output, "wb") as _f:
    _db.dump_db(target, _f, "zip")
_result = {{
    "ok": True,
    "message": "Database '" + target + "' backed up to " + output + ".",
    "data": {{"path": output}},
}}""",
        timeout=600,
    )


def db_restore(
    config: OdooConfig, db_name: str, input_path: str, copy: bool = False
) -> ShellResult:
    return _run(
        config,
        f"""\
from odoo.service import db as _db
target = "{db_name}"
src = {input_path!r}
if _db.exp_db_exist(target):
    raise Exception("Database '" + target + "' already exists. Drop it first or pick a different name.")
_db.restore_db(target, src, copy={bool(copy)})
_result = {{"ok": True, "message": "Database '" + target + "' restored from " + src + "."}}""",
        timeout=600,
    )


def db_duplicate(config: OdooConfig, source: str, target: str) -> ShellResult:
    return _run(
        config,
        f"""\
from odoo.service import db as _db
src = "{source}"
dst = "{target}"
if not _db.exp_db_exist(src):
    raise Exception("Source database '" + src + "' does not exist.")
if _db.exp_db_exist(dst):
    raise Exception("Target database '" + dst + "' already exists.")
_db.exp_duplicate_database(src, dst)
_result = {{"ok": True, "message": "Duplicated '" + src + "' to '" + dst + "'."}}""",
        timeout=600,
    )
