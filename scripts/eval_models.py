"""Прогон тестовых нарядов через под-workflow распознавания и подсчёт точности по полям.

python scripts/eval_models.py --url <webhook-url> [--models m1,m2] [--runs 1]
Результат: eval/results.md (таблица для README/демо) и eval/raw-<model>.json.
Эталон взят из scripts/make_test_orders.py (данные выдуманные).
"""
import argparse
import base64
import json
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "test-data"
OUT = ROOT / "eval"

TRUTH = {
    "order-2481-bridge.jpg": {
        "order_number": "2481", "date": "27.10.2026", "clinic": "Улыбка", "doctor": "Соколова А. В.",
        "patient_initials": "П.И.С.", "teeth": [14, 15, 16], "work_type": "Мост", "units": 3,
        "shade": "A2", "due_date": "03.11.2026",
    },
    "order-2482-emax.jpg": {
        "order_number": "2482", "date": "27.10.2026", "clinic": "Дента-Люкс", "doctor": "Ким Р. Т.",
        "patient_initials": "О.Н.", "teeth": [21], "work_type": "Коронка E.max", "units": 1,
        "shade": "B1", "due_date": "30.10.2026",
    },
    "order-2483-veneers.jpg": {
        "order_number": "2483", "date": "28.10.2026", "clinic": "Стоматология на Морской",
        "doctor": "Гаспарян Л. М.", "patient_initials": "Е.А.", "teeth": [11, 12, 21, 22],
        "work_type": "Винир", "units": 4, "shade": "BL2", "due_date": "10.11.2026",
    },
    # Плохое фото: количество закрыто пятном. Правильное поведение модели —
    # не угадывать (null или низкая уверенность), чтобы наряд ушёл в «ПРОВЕРИТЬ».
    "order-2484-blurry.jpg": {
        "order_number": "2484", "date": "28.10.2026", "clinic": "Улыбка", "doctor": "Соколова А. В.",
        "patient_initials": "Т.А.", "teeth": [36, 37], "work_type": "Коронка цирконий", "units": 2,
        "shade": "A3", "due_date": "05.11.2026",
    },
}
# Цена OpenRouter, $ за 1M токенов (вход, выход) — для оценки стоимости наряда
PRICES = {
    "deepseek/deepseek-v4-flash-vision-exp": (0.2156, 0.6468),
    "anthropic/claude-haiku-4.5": (1.0, 5.0),
    "google/gemma-4-31b-it:free": (0.0, 0.0),
}


def norm(field, v):
    if v is None:
        return None
    if field == "teeth":
        items = v if isinstance(v, list) else re.split(r"\D+", str(v))
        return sorted(int(x) for x in items if str(x).strip())
    if field == "units":
        try:
            return int(float(str(v).replace(",", ".")))
        except ValueError:
            return None
    s = re.sub(r"\s+", "", str(v)).lower().replace("ё", "е")
    if field == "patient_initials":
        s = "".join(w[0] + "." for w in re.split(r"[.\s]+", str(v)) if w).lower()
    return s


def call(url, model, path):
    body = json.dumps({
        "model": model,
        "mime": "image/jpeg",
        "image_b64": base64.b64encode(path.read_bytes()).decode(),
    }).encode()
    req = urllib.request.Request(url, body, {"Content-Type": "application/json"})
    t = time.time()
    with urllib.request.urlopen(req, timeout=180) as r:
        res = json.loads(r.read())
    return (res[0] if isinstance(res, list) else res), time.time() - t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--models", default="deepseek/deepseek-v4-flash-vision-exp")
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)

    lines = ["| Модель | Номер | Кол-во | Остальные поля | Плохое фото → ПРОВЕРИТЬ | Фамилия не утекла | ≈ $/наряд | ≈ сек |",
             "|---|---|---|---|---|---|---|---|"]
    for model in args.models.split(","):
        raw, hit = {}, {"order_number": [0, 0], "units": [0, 0], "rest": [0, 0]}
        flagged_bad, leaked, cost, secs = False, False, 0.0, 0.0
        for fname, truth in TRUTH.items():
            res, dt = call(args.url, model, DATA / fname)
            secs += dt
            fields = res.get("fields", {})
            raw[fname] = res
            u = res.get("usage", {})
            pin, pout = PRICES.get(model, (0, 0))
            cost += (u.get("prompt_tokens", 0) * pin + u.get("completion_tokens", 0) * pout) / 1e6
            if "петров" in json.dumps(fields, ensure_ascii=False).lower():
                leaked = True
            bad = fname.endswith("blurry.jpg")
            for k, expected in truth.items():
                got = (fields.get(k) or {})
                ok = norm(k, got.get("value")) == norm(k, expected)
                conf = float(got.get("confidence") or 0)
                if bad and k == "units":
                    # успех на плохом фото = модель не уверена (наряд уйдёт на проверку)
                    flagged_bad = flagged_bad or conf < 0.9 or got.get("value") is None
                    continue
                bucket = k if k in ("order_number", "units") else "rest"
                hit[bucket][0] += ok
                hit[bucket][1] += 1
            print(f"{model} {fname}: {dt:.1f}s")
        (OUT / f"raw-{model.replace('/', '_').replace(':', '_')}.json").write_text(
            json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
        pct = lambda b: f"{hit[b][0]}/{hit[b][1]} ({100 * hit[b][0] / max(hit[b][1], 1):.0f}%)"
        lines.append(f"| `{model}` | {pct('order_number')} | {pct('units')} | {pct('rest')} | "
                     f"{'да' if flagged_bad else 'нет'} | {'нет' if leaked else 'да'} | "
                     f"{cost / len(TRUTH):.4f} | {secs / len(TRUTH):.0f} |")

    table = "\n".join(lines)
    (OUT / "results.md").write_text("# Точность распознавания на тестовых нарядах\n\n" + table + "\n", encoding="utf-8")
    print(table)


if __name__ == "__main__":
    main()
