"""Export the Attendance Incident Desk configuration as Frappe fixtures.

Run with the bench environment Python:
    env/bin/python apps/iso9001/scripts/export_attendance_incident_fixtures.py optilens.localhost

The regular bench export-fixtures --app iso9001 keeps exporting the other
app fixtures. These separate filenames preserve its current DocType filters.
"""

import json
import os
import re
import sys
from pathlib import Path


def main(site):
    app_root = Path(__file__).resolve().parents[1]
    bench_root = Path(__file__).resolve().parents[3]
    fixtures = app_root / "iso9001" / "fixtures"
    os.chdir(bench_root / "sites")

    import frappe
    from frappe.core.doctype.data_import.data_import import export_json

    frappe.init(site=site)
    frappe.connect()
    frappe.set_user("Administrator")
    try:
        items = [
            ("DocType", "attendance_incident_01_doctype.json", ["Attendance Incident"]),
            ("Client Script", "attendance_incident_02_client_script.json", ["Attendance Incident Form"]),
            (
                "Server Script",
                "attendance_incident_03_server_script.json",
                [
                    "Attendance Incident Prefill",
                    "Attendance Incident Identity",
                    "Attendance Incident Validate",
                    "Attendance Incident Before Submit",
                ],
            ),
            (
                "Print Format",
                "attendance_incident_04_print_format.json",
                ["Rapport de retard ou d'absence"],
            ),
            (
                "Property Setter",
                "attendance_incident_05_property_setter.json",
                ["Attendance Incident-main-default_print_format"],
            ),
            ("Workspace", "attendance_incident_07_workspace.json", ["QM"]),
        ]

        for doctype, filename, names in items:
            missing = [name for name in names if not frappe.db.exists(doctype, name)]
            if missing:
                raise RuntimeError(f"Missing {doctype}: {', '.join(missing)}")
            path = fixtures / filename
            export_json(doctype, str(path), filters={"name": ["in", names]})
            print(f"{filename}: {len(json.loads(path.read_text()))} record(s)")

        incident = frappe.get_doc("DocType", "Attendance Incident")
        sources = {"Attendance Incident", "Attendance Incident Form", "Fiche de poste"}
        for field in incident.fields:
            if field.label:
                sources.add(field.label)
            if field.fieldtype == "Select" and field.options:
                sources.update(item.strip() for item in field.options.splitlines() if item.strip())
        client = frappe.db.get_value("Client Script", "Attendance Incident Form", "script")
        sources.update(re.findall(r'__\("([^"]+)"\)', client))

        translations = frappe.get_all(
            "Translation",
            filters={
                "source_text": ["in", sorted(sources)],
                "language": ["in", ["fr", "en", "ar"]],
            },
            pluck="name",
            limit_page_length=0,
        )
        if not translations:
            raise RuntimeError("No Attendance Incident translations were found")
        path = fixtures / "attendance_incident_06_translation.json"
        export_json("Translation", str(path), filters={"name": ["in", translations]})
        print(f"{path.name}: {len(json.loads(path.read_text()))} record(s)")
    finally:
        frappe.destroy()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: export_attendance_incident_fixtures.py SITE")
    main(sys.argv[1])
