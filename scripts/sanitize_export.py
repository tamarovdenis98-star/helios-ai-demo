"""Очистка экспортированных из n8n workflow перед коммитом.

python scripts/sanitize_export.py   (читает workflows/raw/*.json, пишет workflows/*.json)

- ID credentials, Data Table и workflow заменяются плейсхолдерами REPLACE_*;
- убираются служебные поля (versionId, shared, meta, pinData, id);
- в конце скрипт ищет в результате всё, похожее на секреты, и падает, если нашёл.
Сами секреты в экспорт n8n не попадают: там только ссылки на credentials.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "workflows" / "raw"
OUT = ROOT / "workflows"

# Человекочитаемые плейсхолдеры для ID, известных по этому проекту
PLACEHOLDERS = {
    "SKaDJlye4Rovx0bY": "REPLACE_DATATABLE_helios_config",
    "Oh1JrbIa19dNCX0M": "REPLACE_DATATABLE_helios_courses",
    "hp1NMC1E1GusmQ9g": "REPLACE_WORKFLOW_HELIOS_02_recognize",
    "E4tuEUavUZCpHlvx": "REPLACE_WORKFLOW_HELIOS_99_errors",
}
DROP_KEYS = {"id", "versionId", "activeVersionId", "versionCounter", "shared", "meta", "pinData",
             "staticData", "createdAt", "updatedAt", "isArchived", "triggerCount", "tags", "active",
             "sourceWorkflowId", "description", "nodeGroups"}
SECRET_PATTERNS = [
    r"sk-or-v1-[0-9a-f]{20,}", r"sk-ant-[A-Za-z0-9_-]{20,}", r"\b\d{8,10}:[A-Za-z0-9_-]{30,}\b",
    r"GOCSPX-[A-Za-z0-9_-]{10,}", r"/rest/\d+/[a-z0-9]{10,}", r"\d{6,}-[a-z0-9]{20,}\.apps\.googleusercontent\.com",
    r"docs\.google\.com/spreadsheets/d/[A-Za-z0-9_-]{30,}", r"drive\.google\.com/drive/folders/[A-Za-z0-9_-]{20,}",
]


def clean(wf):
    for k in DROP_KEYS:
        wf.pop(k, None)
    for node in wf.get("nodes", []):
        for cred in (node.get("credentials") or {}).values():
            cred["id"] = "REPLACE_CREDENTIAL_ID"
    if "settings" in wf:
        wf["settings"] = {k: v for k, v in wf["settings"].items() if k in
                          ("executionOrder", "timezone", "errorWorkflow", "saveDataErrorExecution",
                           "saveDataSuccessExecution")}
    text = json.dumps(wf, ensure_ascii=False, indent=2)
    for real, ph in PLACEHOLDERS.items():
        text = text.replace(real, ph)
    return text


def slug(name):
    m = re.match(r"HELIOS (\d+)", name)
    tail = {"01": "orders-photo-to-sheet", "02": "recognize-order-llm", "03": "kb-consultant",
            "99": "error-alerts"}.get(m.group(1) if m else "", re.sub(r"\W+", "-", name.lower()))
    return f"{m.group(1) if m else 'xx'}-{tail}.json"


def main():
    files = sorted(RAW.glob("*.json"))
    if not files:
        sys.exit(f"нет файлов в {RAW}")
    found = []
    for f in files:
        wf = json.loads(f.read_text(encoding="utf-8"))
        text = clean(wf)
        target = OUT / slug(wf.get("name", f.stem))
        target.write_text(text + "\n", encoding="utf-8")
        for pat in SECRET_PATTERNS:
            if re.search(pat, text):
                found.append(f"{target.name}: {pat}")
        print("ok", target.name)
    if found:
        sys.exit("НАЙДЕНЫ ПОХОЖИЕ НА СЕКРЕТЫ:\n" + "\n".join(found))
    print("секретов не найдено")


if __name__ == "__main__":
    main()
