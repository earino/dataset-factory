# Dump Socrata view column metadata (names, field names, descriptions, types)
import json, sys

view_id = sys.argv[1]
d = json.load(open(f"view_{view_id}.json"))
print(f"== {view_id}: {d.get('name')} ==")
for c in d.get("columns", []):
    name = c.get("name")
    fn = c.get("fieldName")
    t = c.get("dataTypeName")
    desc = (c.get("description") or "").replace("\n", " ")[:120]
    cached = c.get("cachedContents", {}).get("non_null", "?")
    print(f"{fn:38s} | {t:14s} | n={cached:>8} | {name} | {desc}")
