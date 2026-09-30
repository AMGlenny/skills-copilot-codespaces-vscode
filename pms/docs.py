"""Data dictionary and data model diagram, generated from the schema."""
from .schema import LISTS

TYPE_LABELS = {
    "text": "text", "note": "long text", "number": "number", "integer": "whole number",
    "bool": "true/false", "date": "date (YYYY-MM-DD)", "datetime": "date-time (UTC, ISO 8601)",
    "choice": "choice",
}

DICT_HEADER = ["table_name", "column_name", "data_type", "required", "indexed", "unique",
               "allowed_values", "references", "description"]


def dictionary_rows():
    rows = []
    for lst in LISTS:
        for i, col in enumerate(lst.all_columns):
            is_key = i == 0
            rows.append(dict(
                table_name=lst.name, column_name=col.name, data_type=TYPE_LABELS[col.type],
                required="true" if col.required else "false",
                indexed="true" if col.indexed else "false",
                unique="true" if is_key and lst.unique_key else "false",
                allowed_values="|".join(col.choices) if col.choices else "",
                references=col.ref or "", description=col.description,
            ))
    return rows


def _md_cell(text):
    return str(text).replace("|", "\\|").replace("\n", " ")


def dictionary_markdown():
    out = ["# Data dictionary", "",
           "_Generated from `pms/schema.py`. Do not edit by hand: change the schema and run `python -m pms build`._", ""]
    domains = {"measures": "Measures", "weekly_work": "Weekly work", "shared": "Shared", "reporting": "Reporting"}
    for domain, title in domains.items():
        out += [f"## {title}", ""]
        for lst in [x for x in LISTS if x.domain == domain]:
            flags = []
            if lst.restricted:
                flags.append("restricted")
            if lst.generated:
                flags.append("written by flows only")
            if not lst.exported:
                flags.append("excluded from standard exports and AI snapshots")
            out += [f"### {lst.name}", "", lst.description + (f" ({'; '.join(flags)})" if flags else ""), "",
                    "| column | type | required | notes |", "|---|---|---|---|"]
            for i, col in enumerate(lst.all_columns):
                notes = col.description
                if i == 0:
                    notes = f"**Key** (SharePoint Title column). {notes}"
                if col.choices:
                    notes += f" Values: `{'`, `'.join(col.choices)}`."
                if col.ref:
                    notes += f" Links to `{col.ref}`."
                out.append(f"| `{col.name}` | {TYPE_LABELS[col.type]} | {'yes' if col.required else ''} | {_md_cell(notes)} |")
            out.append("")
    return "\n".join(out)


def mermaid():
    lines = ["erDiagram"]
    for lst in LISTS:
        lines.append(f"    {lst.name} {{")
        for i, col in enumerate(lst.all_columns):
            if i == 0 or col.ref:
                t = "string" if col.type in ("text", "note", "choice") else col.type
                tag = " PK" if i == 0 else " FK"
                lines.append(f"        {t} {col.name}{tag}")
        lines.append("    }")
    seen = set()
    for lst in LISTS:
        for col in lst.columns:
            if not col.ref:
                continue
            target = col.ref.split(".")[0]
            pair = (target, lst.name, col.name)
            if pair in seen:
                continue
            seen.add(pair)
            lines.append(f'    {target} ||--o{{ {lst.name} : "{col.name}"')
    return "\n".join(lines)
