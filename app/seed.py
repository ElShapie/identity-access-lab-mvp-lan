"""Crea perfiles de directorio y las cuentas demo heredadas."""
import json
import os
from pathlib import Path
from app.store import Store

store = Store(os.environ.get("APP_DB", "/srv/data/lab.sqlite"))
records_path = Path(os.environ.get("DIRECTORY_ACCOUNTS_FILE", "/srv/directory/accounts.json"))
if records_path.exists():
    for record in json.loads(records_path.read_text(encoding="utf-8")):
        email = record["userName"].strip().lower()
        profile = {key: record[key] for key in ("userName", "title", "active", "displayName", "department", "employeeNumber") if key in record}
        current = store.by_name(email)
        if current is None:
            store.save(profile)
        else:
            identity_fields = {key: profile[key] for key in ("displayName", "department", "employeeNumber") if key in profile}
            if any(current.get(key) != value for key, value in identity_fields.items()):
                store.save(identity_fields, current["id"])

LEGACY_USERS = (
    ("ingeniero@example.test", "mantenimiento", "Ingeniero de laboratorio", "TI"),
    ("auditor@example.test", "auditor", "Auditor de laboratorio", "SOC / Auditoría"),
    ("admin@example.test", "auditor", "Administrador legado", "IAM"),
    ("rrhh@example.test", "consulta", "Encargado de RRHH", "RRHH"),
    ("ti@example.test", "mantenimiento", "Encargado de TI", "TI"),
    ("iam@example.test", "admin", "Encargado de IAM", "IAM"),
    ("soc-auditoria@example.test", "auditor", "Encargado de SOC / Auditoría", "SOC / Auditoría"),
    ("seguridad-fisica@example.test", "consulta", "Encargado de Seguridad Física", "Seguridad Física"),
)
for email, role, display_name, department in LEGACY_USERS:
    profile = {"userName": email, "title": role, "active": True, "displayName": display_name, "department": department}
    current = store.by_name(email)
    if current is None:
        store.save(profile)
    elif any(current.get(key) != value for key, value in profile.items() if key != "userName"):
        store.save(profile, current["id"])

