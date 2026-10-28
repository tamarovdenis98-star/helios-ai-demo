"""Генератор бланка наряда HELIOS и тестовых заполненных нарядов.

python scripts/make_test_orders.py  ->  test-data/*.png, test-data/blank-order.pdf
Все данные выдуманные. На бланке 1 пациент записан с фамилией нарочно:
workflow обязан сохранить только инициалы (152-ФЗ).
"""
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path(__file__).resolve().parent.parent / "test-data"
FONTS = "C:/Windows/Fonts/"
W, H = 1240, 1754  # A4 @150dpi

PRINT = ImageFont.truetype(FONTS + "arial.ttf", 26)
PRINT_SMALL = ImageFont.truetype(FONTS + "arial.ttf", 20)
PRINT_BOLD = ImageFont.truetype(FONTS + "arialbd.ttf", 30)
TITLE = ImageFont.truetype(FONTS + "arialbd.ttf", 44)
HAND_FONTS = ["segoepr.ttf", "segoesc.ttf"]

WORK_TYPES = [
    "Коронка цирконий", "Коронка E.max", "Металлокерамика",
    "Винир", "Мост", "Вкладка", "Другое",
]
UPPER = [18, 17, 16, 15, 14, 13, 12, 11, 21, 22, 23, 24, 25, 26, 27, 28]
LOWER = [48, 47, 46, 45, 44, 43, 42, 41, 31, 32, 33, 34, 35, 36, 37, 38]

# Координаты полей бланка: (подпись, y, x начала линии)
FIELDS = {
    "date": ("Дата приёма", 250, 300),
    "clinic": ("Клиника", 330, 300),
    "doctor": ("Врач", 410, 300),
    "patient": ("Пациент (инициалы)", 490, 380),
    "units": ("Количество единиц", 1180, 380),
    "shade": ("Цвет (VITA)", 1260, 380),
    "due": ("Срок сдачи", 1340, 380),
    "comment": ("Комментарий", 1420, 300),
}
NUMBER_POS = (760, 110)
CHART_TOP = 600
WORK_TOP = 900


def tooth_cell(tooth):
    """Левый верхний угол клетки зуба в зубной формуле."""
    row, idx = (0, UPPER.index(tooth)) if tooth in UPPER else (1, LOWER.index(tooth))
    x = 80 + idx * 67 + (20 if idx >= 8 else 0)
    y = CHART_TOP + 60 + row * 110
    return x, y


def draw_blank():
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    d.text((80, 60), "HELIOS", font=TITLE, fill="#1d4e89")
    d.text((80, 112), "зуботехническая лаборатория", font=PRINT_SMALL, fill="#555")
    d.text((470, 110), "НАРЯД-ЗАКАЗ №", font=PRINT_BOLD, fill="black")
    d.rectangle([750, 95, 1000, 155], outline="black", width=3)
    d.line([80, 190, W - 80, 190], fill="#1d4e89", width=4)

    for key, (label, y, x0) in FIELDS.items():
        d.text((80, y - 30), label + ":", font=PRINT, fill="black")
        d.line([x0, y + 8, W - 80, y + 8], fill="#888", width=2)
    d.text((W - 470, FIELDS["patient"][1] + 16),
           "ФИО полностью не указывать (152-ФЗ)", font=PRINT_SMALL, fill="#b00")

    d.text((80, CHART_TOP), "Зубная формула (FDI) — отметьте зубы крестиком:",
           font=PRINT, fill="black")
    for tooth in UPPER + LOWER:
        x, y = tooth_cell(tooth)
        d.rectangle([x, y, x + 60, y + 60], outline="black", width=2)
        d.text((x + 14, y + 64), str(tooth), font=PRINT_SMALL, fill="black")
    mid = tooth_cell(21)[0] - 12
    d.line([mid, CHART_TOP + 50, mid, CHART_TOP + 290], fill="#1d4e89", width=3)

    d.text((80, WORK_TOP), "Вид работы:", font=PRINT, fill="black")
    for i, wt in enumerate(WORK_TYPES):
        x = 80 + (i % 4) * 280
        y = WORK_TOP + 50 + (i // 4) * 60
        d.rectangle([x, y, x + 32, y + 32], outline="black", width=2)
        d.text((x + 44, y), wt, font=PRINT, fill="black")
    d.text((80, WORK_TOP + 190), "Зубы через запятую:", font=PRINT, fill="black")
    d.line([360, WORK_TOP + 198, W - 80, WORK_TOP + 198], fill="#888", width=2)

    d.line([80, 1600, W - 80, 1600], fill="#1d4e89", width=2)
    d.text((80, 1615), "Подпись врача ____________     Принял техник ____________",
           font=PRINT, fill="black")
    return img


def hand(d, xy, text, size=38, color=(20, 40, 140), jitter=4, font=None):
    """Текст «от руки»: рукописный шрифт, лёгкий разброс по высоте букв."""
    f = ImageFont.truetype(FONTS + (font or random.choice(HAND_FONTS)), size)
    x, y = xy
    for ch in text:
        d.text((x, y + random.randint(-jitter, jitter)), ch, font=f, fill=color)
        x += f.getlength(ch) + random.uniform(-1, 1.5)


def cross(d, cx, cy, s=22, color=(20, 40, 140), w=4):
    d.line([cx - s, cy - s, cx + s, cy + s], fill=color, width=w)
    d.line([cx - s, cy + s, cx + s, cy - s], fill=color, width=w)


def fill(order, bad=False):
    img = draw_blank()
    d = ImageDraw.Draw(img)
    color = (90, 90, 120) if bad else (20, 40, 140)
    jit = 9 if bad else 4
    size = 34 if bad else 38

    hand(d, (NUMBER_POS[0] + 10, NUMBER_POS[1] - 8), order["number"], 44, color, jit)
    for key in ["date", "clinic", "doctor", "patient", "units", "shade", "due", "comment"]:
        _, y, x0 = FIELDS[key]
        hand(d, (x0 + 10, y - 48), order[key], size, color, jit)

    for t in order["teeth"]:
        x, y = tooth_cell(t)
        cross(d, x + 30, y + 30, color=color)
    hand(d, (370, WORK_TOP + 150), ", ".join(map(str, order["teeth"])), size, color, jit)

    i = WORK_TYPES.index(order["work"])
    x = 80 + (i % 4) * 280
    y = WORK_TOP + 50 + (i // 4) * 60
    cross(d, x + 16, y + 16, 18, color)

    if bad:
        # пятно, засвет и смаз — «фото на телефон в лаборатории»
        stain = Image.new("L", (W, H), 0)
        sd = ImageDraw.Draw(stain)
        sd.ellipse([330, 1090, 640, 1250], fill=215)  # прямо на «Количество единиц»
        sd.ellipse([720, 70, 960, 190], fill=120)     # краешек на номере наряда
        stain = stain.filter(ImageFilter.GaussianBlur(28))
        img = Image.composite(Image.new("RGB", (W, H), (150, 115, 70)), img, stain)
        img = img.filter(ImageFilter.GaussianBlur(2.4))

    # фото, а не скан: поворот, фон стола, лёгкая неравномерность
    angle = random.uniform(-6, -3) if bad else random.uniform(-2, 2)
    img = img.rotate(angle, expand=True, fillcolor=(120, 110, 95))
    bg = Image.new("RGB", (img.width + 120, img.height + 120), (120, 110, 95))
    bg.paste(img, (60, 60))
    shade = Image.linear_gradient("L").resize(bg.size).point(lambda v: int(v * (0.45 if bad else 0.18)))
    bg = Image.composite(Image.new("RGB", bg.size, (0, 0, 0)), bg, shade)
    return bg.resize((bg.width * 2 // 3, bg.height * 2 // 3))


ORDERS = [
    {   # фамилия на бланке нарочно: в таблицу должны попасть только инициалы
        "file": "order-2481-bridge.jpg", "number": "2481", "date": "27.10.2026",
        "clinic": "Улыбка", "doctor": "Соколова А. В.", "patient": "Петров И. С.",
        "teeth": [14, 15, 16], "work": "Мост", "units": "3", "shade": "A2",
        "due": "03.11.2026", "comment": "Металлокерамика, опоры 14 и 16",
    },
    {
        "file": "order-2482-emax.jpg", "number": "2482", "date": "27.10.2026",
        "clinic": "Дента-Люкс", "doctor": "Ким Р. Т.", "patient": "О. Н.",
        "teeth": [21], "work": "Коронка E.max", "units": "1", "shade": "B1",
        "due": "30.10.2026", "comment": "Срочно, примерка в пятницу",
    },
    {
        "file": "order-2483-veneers.jpg", "number": "2483", "date": "28.10.2026",
        "clinic": "Стоматология на Морской", "doctor": "Гаспарян Л. М.", "patient": "Е. А.",
        "teeth": [12, 11, 21, 22], "work": "Винир", "units": "4", "shade": "BL2",
        "due": "10.11.2026", "comment": "Мок-ап согласован с пациентом",
    },
    {   # нарочно плохо читаемый: смаз, пятно на количестве, сильный наклон
        "file": "order-2484-blurry.jpg", "number": "2484", "date": "28.10.2026",
        "clinic": "Улыбка", "doctor": "Соколова А. В.", "patient": "Т. А.",
        "teeth": [36, 37], "work": "Коронка цирконий", "units": "2", "shade": "A3",
        "due": "05.11.2026", "comment": "Учесть прикус, см. слепок", "bad": True,
    },
]


def work_photo():
    """Условное «фото готовой работы» для сценария 2."""
    img = Image.new("RGB", (900, 700), (40, 44, 52))
    d = ImageDraw.Draw(img)
    for i, x in enumerate([230, 450, 670]):
        d.rounded_rectangle([x - 90, 220, x + 90, 470], 60, fill=(236, 230, 214), outline=(200, 190, 170), width=4)
        d.ellipse([x - 60, 250, x + 10, 300], fill=(250, 248, 240))
    d.text((40, 620), "HELIOS · демо-фото работы", font=PRINT, fill=(180, 180, 180))
    return img


def main():
    random.seed(7)
    OUT.mkdir(exist_ok=True)
    blank = draw_blank()
    blank.save(OUT / "blank-order.png")
    blank.save(OUT / "blank-order.pdf", resolution=150)
    for o in ORDERS:
        fill(o, o.get("bad", False)).save(OUT / o["file"], quality=85 if not o.get("bad") else 55)
    work_photo().save(OUT / "work-photo-2481.jpg", quality=85)
    print("saved to", OUT)


if __name__ == "__main__":
    main()
