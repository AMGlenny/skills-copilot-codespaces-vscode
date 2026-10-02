/**
 * PMSExport: Office Script used by the PMSExportRun flow.
 *
 * Writes one page of tidy rows into an Excel table and returns the same
 * rows as CSV text, so the .xlsx and .csv files always match.
 *
 * payload (JSON text):
 *   { "mode": "table", "table": {...}, "items": [...], "lookups": {...}, "first": true }
 *     - table:   one table definition from export_definitions.json
 *     - items:   SharePoint REST items (odata=nometadata), up to about 1,000
 *     - lookups: { people: [...], org_units: [...], groups: [...], measures: [...] }
 *     - first:   true on the first page (creates the sheet and header row)
 *   { "mode": "dictionary", "rows": [[table, column, type, description], ...] }
 *
 * Returns CSV text (CRLF line endings). The header row is only included on
 * the first page. The flow adds the byte order mark when it creates the file.
 *
 * The transform functions mirror pms/exports.py exactly; tests/test_exports.py
 * runs both and compares the output.
 *
 * To install: Excel for the web > Automate > New script, paste this file,
 * and save it as "PMSExport" (in the account the flows use).
 */

interface LookupRef {
  table: string;
  field: string;
}

interface ColumnDef {
  name: string;
  type: string;
  description: string;
  source?: string;
  lookup_from?: string;
  lookup?: LookupRef[];
}

interface TableDef {
  name: string;
  columns: ColumnDef[];
}

interface SpItem {
  [key: string]: string | number | boolean | null;
}

interface LookupTables {
  [table: string]: SpItem[];
}

interface Payload {
  mode: string;
  table?: TableDef;
  items?: SpItem[];
  lookups?: LookupTables;
  first?: boolean;
  rows?: string[][];
}

type Cell = string | number | boolean;

// ---------------------------------------------------------------------------
// Transform (mirrors pms/exports.py)
// ---------------------------------------------------------------------------

function lastSundayUtc(year: number, month: number): number {
  // month is 1-12. Returns 01:00 UTC on the last Sunday of that month.
  const last = new Date(Date.UTC(year, month, 0));
  const back = last.getUTCDay();
  return Date.UTC(year, month - 1, last.getUTCDate() - back, 1);
}

function parseUtc(iso: string): number {
  let s = iso;
  if (!/[zZ]|[+-]\d\d:\d\d$/.test(s)) {
    s = s + "Z";
  }
  return Date.parse(s);
}

function pad(n: number): string {
  return n < 10 ? "0" + n : String(n);
}

function ukDate(iso: string): string {
  const ms = parseUtc(iso);
  const year = new Date(ms).getUTCFullYear();
  const bst = ms >= lastSundayUtc(year, 3) && ms < lastSundayUtc(year, 10);
  const d = new Date(ms + (bst ? 3600000 : 0));
  return d.getUTCFullYear() + "-" + pad(d.getUTCMonth() + 1) + "-" + pad(d.getUTCDate());
}

function utcDateTime(iso: string): string {
  const d = new Date(parseUtc(iso));
  return d.getUTCFullYear() + "-" + pad(d.getUTCMonth() + 1) + "-" + pad(d.getUTCDate()) +
    "T" + pad(d.getUTCHours()) + ":" + pad(d.getUTCMinutes()) + ":" + pad(d.getUTCSeconds()) + "Z";
}

function lookupMaps(lookups: LookupTables): Map<string, Map<string, SpItem>> {
  const maps = new Map<string, Map<string, SpItem>>();
  for (const table of Object.keys(lookups)) {
    const m = new Map<string, SpItem>();
    for (const row of lookups[table]) {
      m.set(String(row["Title"]), row);
    }
    maps.set(table, m);
  }
  return maps;
}

function cellValue(col: ColumnDef, item: SpItem, maps: Map<string, Map<string, SpItem>>): Cell {
  if (col.lookup && col.lookup.length > 0) {
    const key = item[col.lookup_from as string];
    if (key === null || key === undefined || key === "") {
      return "";
    }
    for (const lk of col.lookup) {
      const table = maps.get(lk.table);
      const row = table ? table.get(String(key)) : undefined;
      if (row && row[lk.field] !== null && row[lk.field] !== undefined && row[lk.field] !== "") {
        return String(row[lk.field]);
      }
    }
    return "";
  }
  const v = item[col.source as string];
  if (v === null || v === undefined || v === "") {
    return "";
  }
  switch (col.type) {
    case "date":
      return ukDate(String(v));
    case "datetime":
      return utcDateTime(String(v));
    case "number":
      return Number(v);
    case "bool":
      return v === true || v === "true";
    default:
      return String(v);
  }
}

function transform(table: TableDef, items: SpItem[], lookups: LookupTables): Cell[][] {
  const maps = lookupMaps(lookups);
  return items.map((item) => table.columns.map((c) => cellValue(c, item, maps)));
}

function csvField(v: Cell): string {
  if (v === "") {
    return "";
  }
  if (typeof v === "boolean") {
    return v ? "true" : "false";
  }
  if (typeof v === "number") {
    return String(v);
  }
  const s = String(v);
  if (/[",\r\n]/.test(s) || s !== s.trim()) {
    return '"' + s.split('"').join('""') + '"';
  }
  return s;
}

function toCsv(headers: string[], rows: Cell[][], includeHeader: boolean): string {
  const lines: string[] = includeHeader ? [headers.join(",")] : [];
  for (const r of rows) {
    lines.push(r.map(csvField).join(","));
  }
  return lines.map((l) => l + "\r\n").join("");
}

// ---------------------------------------------------------------------------
// Excel
// ---------------------------------------------------------------------------

function excelSerial(value: string, withTime: boolean): number {
  const y = Number(value.substring(0, 4));
  const m = Number(value.substring(5, 7));
  const d = Number(value.substring(8, 10));
  let ms = Date.UTC(y, m - 1, d);
  if (withTime) {
    ms += Number(value.substring(11, 13)) * 3600000 + Number(value.substring(14, 16)) * 60000 +
      Number(value.substring(17, 19)) * 1000;
  }
  return (ms - Date.UTC(1899, 11, 30)) / 86400000;
}

function numberFormat(type: string): string {
  if (type === "date") {
    return "yyyy-mm-dd";
  }
  if (type === "datetime") {
    return "yyyy-mm-dd hh:mm:ss";
  }
  if (type === "text") {
    // Stops Excel turning "1.10" or "0012" into numbers.
    return "@";
  }
  return "General";
}

function columnLetter(index: number): string {
  let n = index + 1;
  let s = "";
  while (n > 0) {
    const r = (n - 1) % 26;
    s = String.fromCharCode(65 + r) + s;
    n = Math.floor((n - 1) / 26);
  }
  return s;
}

function writeTable(workbook: ExcelScript.Workbook, table: TableDef, rows: Cell[][], first: boolean) {
  const headers = table.columns.map((c) => c.name);
  const values: (string | number | boolean)[][] = rows.map((r) =>
    r.map((v, i) => {
      const t = table.columns[i].type;
      if (v !== "" && (t === "date" || t === "datetime")) {
        return excelSerial(String(v), t === "datetime");
      }
      return v;
    })
  );
  const sheet = workbook.getWorksheet(table.name);
  if (first || !sheet) {
    if (sheet) {
      sheet.delete();
    }
    const ns = workbook.addWorksheet(table.name);
    table.columns.forEach((c, i) => {
      const letter = columnLetter(i);
      ns.getRange(letter + ":" + letter).setNumberFormat(numberFormat(c.type));
    });
    ns.getRangeByIndexes(0, 0, 1, headers.length).setValues([headers]);
    ns.getFreezePanes().freezeRows(1);
    if (values.length > 0) {
      ns.getRangeByIndexes(1, 0, values.length, headers.length).setValues(values);
      const t = ns.addTable(ns.getRangeByIndexes(0, 0, values.length + 1, headers.length), true);
      t.setName("tbl_" + table.name);
      t.setShowBandedRows(false);
    }
    return;
  }
  if (values.length === 0) {
    return;
  }
  const existing = sheet.getTable("tbl_" + table.name);
  if (existing) {
    existing.addRows(undefined, values);
  } else {
    const used = sheet.getUsedRange();
    const start = used ? used.getRowCount() : 1;
    sheet.getRangeByIndexes(start, 0, values.length, headers.length).setValues(values);
  }
}

function removeDefaultSheet(workbook: ExcelScript.Workbook) {
  for (const name of ["Sheet1", "Sheet 1"]) {
    const s = workbook.getWorksheet(name);
    if (s && workbook.getWorksheets().length > 1 && !s.getUsedRange()) {
      s.delete();
    }
  }
}

function main(workbook: ExcelScript.Workbook, payload: string): string {
  const p = JSON.parse(payload) as Payload;
  if (p.mode === "dictionary") {
    const dict: TableDef = {
      name: "data_dictionary",
      columns: ["table_name", "column_name", "data_type", "description"].map((n) => ({
        name: n, type: "text", description: "", source: n,
      })),
    };
    const rows: Cell[][] = (p.rows || []).map((r) => r.map((v) => String(v)));
    writeTable(workbook, dict, rows, true);
    removeDefaultSheet(workbook);
    return toCsv(dict.columns.map((c) => c.name), rows, true);
  }
  const table = p.table as TableDef;
  const rows = transform(table, p.items || [], p.lookups || {});
  writeTable(workbook, table, rows, p.first === true);
  return toCsv(table.columns.map((c) => c.name), rows, p.first === true);
}
