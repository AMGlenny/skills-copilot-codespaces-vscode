"""Turns the schema and seed data into SharePoint REST requests.

Each request is a plain JSON object:
    {"step", "description", "method", "uri", "headers", "body"}
The same files are replayed by the Power Automate setup flow ("Send an HTTP
request to SharePoint") or by scripts/Invoke-PmsSetup.ps1 (PnP PowerShell).
"""
from datetime import date, datetime
from xml.sax.saxutils import escape, quoteattr

from .schema import LIBRARIES, LISTS

VERBOSE = {"Accept": "application/json;odata=verbose", "Content-Type": "application/json;odata=verbose"}
NOMETA = {"Accept": "application/json;odata=nometadata", "Content-Type": "application/json;odata=nometadata"}
MERGE = dict(VERBOSE, **{"X-HTTP-Method": "MERGE", "IF-MATCH": "*"})

# 8 = use the Name attribute as the internal name, 16 = add to default view
FIELD_OPTIONS = 8 | 16

SP_TYPES = {
    "text": "Text", "note": "Note", "number": "Number", "integer": "Number",
    "bool": "Boolean", "date": "DateTime", "datetime": "DateTime", "choice": "Choice",
}


def _list_uri(name):
    return f"_api/web/lists/getbytitle('{name}')"


def field_xml(col):
    attrs = {
        "Type": SP_TYPES[col.type],
        "Name": col.name,
        "StaticName": col.name,
        "DisplayName": col.name,
        "Description": col.description,
        "Required": "TRUE" if col.required else "FALSE",
    }
    if col.indexed:
        attrs["Indexed"] = "TRUE"
    if col.type == "text":
        attrs["MaxLength"] = "255"
    elif col.type == "note":
        attrs.update(NumLines="6", RichText="FALSE", AppendOnly="FALSE")
    elif col.type == "integer":
        attrs["Decimals"] = "0"
    elif col.type == "date":
        attrs["Format"] = "DateOnly"
    elif col.type == "datetime":
        attrs["Format"] = "DateTime"
    elif col.type == "choice":
        attrs.update(Format="Dropdown", FillInChoice="FALSE")
    inner = ""
    if col.default is not None:
        d = col.default
        if col.type == "bool":
            d = "1" if d else "0"
        inner += f"<Default>{escape(str(d))}</Default>"
    if col.choices:
        inner += "<CHOICES>" + "".join(f"<CHOICE>{escape(c)}</CHOICE>" for c in col.choices) + "</CHOICES>"
    attr_text = " ".join(f"{k}={quoteattr(v)}" for k, v in attrs.items())
    return f"<Field {attr_text}>{inner}</Field>" if inner else f"<Field {attr_text}/>"


def schema_requests():
    reqs = []

    def add(desc, uri, body, headers=VERBOSE):
        reqs.append(dict(description=desc, method="POST", uri=uri, headers=headers, body=body))

    for lst in LISTS:
        add(f"Create list {lst.name}", "_api/web/lists", {
            "__metadata": {"type": "SP.List"},
            "BaseTemplate": 100,
            "Title": lst.name,
            "Description": lst.description,
            "EnableVersioning": not lst.generated,
            "NoCrawl": lst.restricted,
        })
        title_uri = f"{_list_uri(lst.name)}/fields/getbyinternalnameortitle('Title')"
        add(f"{lst.name}: rename Title to {lst.key}", title_uri, {
            "__metadata": {"type": "SP.Field"},
            "Title": lst.key,
            "Description": lst.key_description,
            "Indexed": True,
            "Required": lst.key_required,
        }, MERGE)
        if lst.unique_key:
            add(f"{lst.name}: make {lst.key} unique", title_uri,
                {"__metadata": {"type": "SP.Field"}, "EnforceUniqueValues": True}, MERGE)
        for col in lst.columns:
            add(f"{lst.name}: add column {col.name}", f"{_list_uri(lst.name)}/fields/createfieldasxml", {
                "parameters": {
                    "__metadata": {"type": "SP.XmlSchemaFieldCreationInformation"},
                    "SchemaXml": field_xml(col),
                    "Options": FIELD_OPTIONS,
                }
            })
        if lst.read_own_only or lst.edit_own_only:
            # ReadSecurity 1 = all items, 2 = own items. WriteSecurity 1 = all, 2 = own.
            add(f"{lst.name}: item-level permissions", _list_uri(lst.name), {
                "__metadata": {"type": "SP.List"},
                "ReadSecurity": 2 if lst.read_own_only else 1,
                "WriteSecurity": 2 if lst.edit_own_only else 1,
            }, MERGE)
        for view in lst.views:
            fields = ["LinkTitle" if f == "Title" else f for f in view.columns]
            order = f"<OrderBy><FieldRef Name='{view.order_by}' Ascending='{'TRUE' if view.ascending else 'FALSE'}'/></OrderBy>"
            where = f"<Where>{view.where}</Where>" if view.where else ""
            add(f"{lst.name}: add view {view.name}", f"{_list_uri(lst.name)}/views/add", {
                "parameters": {
                    "__metadata": {"type": "SP.ViewCreationInformation"},
                    "Title": view.name,
                    "ViewFields": {"__metadata": {"type": "Collection(Edm.String)"}, "results": fields},
                    "Query": where + order,
                    "RowLimit": 100,
                    "Paged": True,
                    "PersonalView": False,
                    "SetAsDefaultView": False,
                    "ViewTypeKind": 1,
                }
            })
    for name, desc in LIBRARIES:
        add(f"Create document library {name}", "_api/web/lists", {
            "__metadata": {"type": "SP.List"}, "BaseTemplate": 101, "Title": name, "Description": desc,
            "EnableVersioning": True,
        })
    return _number(reqs)


def rest_value(col_type, value):
    if value is None:
        return None
    if col_type == "date":
        # Midday UTC keeps date-only values on the same day in any UK timezone.
        return f"{value.isoformat()}T12:00:00Z"
    if col_type == "datetime":
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")
    return value


def item_requests(data):
    reqs = []
    for lst in LISTS:
        cols = lst.all_columns
        for row in data.get(lst.name, []):
            body = {}
            for col in cols:
                v = rest_value(col.type, row.get(col.name))
                if v is None:
                    continue
                body["Title" if col.name == lst.key else col.name] = v
            reqs.append(dict(description=f"{lst.name}: add {row[lst.key]}", method="POST",
                             uri=f"{_list_uri(lst.name)}/items", headers=NOMETA, body=body))
    return _number(reqs)


def _number(reqs):
    for i, r in enumerate(reqs, 1):
        r["step"] = i
    return [dict(step=r["step"], description=r["description"], method=r["method"], uri=r["uri"],
                 headers=r["headers"], body=r["body"]) for r in reqs]


def csv_value(col_type, value):
    """Tidy export format: ISO dates, true/false, numbers as numbers, blanks as blanks."""
    if value is None:
        return ""
    if col_type == "date":
        return value.isoformat() if isinstance(value, date) else value
    if col_type == "datetime":
        return value.strftime("%Y-%m-%dT%H:%M:%SZ") if isinstance(value, datetime) else value
    if col_type == "bool":
        return "true" if value else "false"
    return value
