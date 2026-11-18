import os
import platform
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox

import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageDraw, ImageFont, ImageTk

# Tesseract: на Windows он у нас установлен в нестандартную папку,
# на Linux обычно лежит в PATH (/usr/bin/tesseract), поэтому путь не задаём
TESSERACT_WINDOWS_PATH = r"C:\Tesseract-OCR\tesseract.exe"

if platform.system() == "Windows" and os.path.exists(TESSERACT_WINDOWS_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_WINDOWS_PATH
else:
    tesseract_in_path = shutil.which("tesseract")
    if tesseract_in_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_in_path

# Максимальный размер картинки, который показываем в окне
PREVIEW_MAX_WIDTH = 900
PREVIEW_MAX_HEIGHT = 720

# Сколько строк распознанного текста максимум рисуем на картинке.
# Иначе для целой страницы текста полоса становится огромной, а после
# уменьшения превью текст превращается в нечитаемые точки
MAX_TEXT_LINES = 12

# Шрифты для подписи (первый найденный). Кириллицу поддерживают Arial и DejaVu Sans
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
    r"C:\Windows\Fonts\tahoma.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
]

# Глобальная ссылка на картинку, иначе tkinter её удалит сборщик мусора
photo = None


def load_cv_image(path):
    """Загружает изображение через OpenCV (с запасным вариантом для путей с кириллицей)."""
    image = cv2.imread(path)
    if image is None:
        data = np.fromfile(path, dtype=np.uint8)
        image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    return image


def find_font_path():
    """Ищет файл шрифта с поддержкой кириллицы. Возвращает None, если не нашёл."""
    for font_path in FONT_CANDIDATES:
        if os.path.exists(font_path):
            return font_path
    return None


def get_font(size):
    """Возвращает TrueType-шрифт нужного размера, иначе стандартный шрифт Pillow."""
    font_path = find_font_path()
    if font_path is not None:
        try:
            return ImageFont.truetype(font_path, size)
        except OSError:
            pass
    return ImageFont.load_default()


def wrap_text(text, font, max_width):
    """Разбивает текст на строки так, чтобы они влезали в max_width пикселей."""
    lines = []
    for paragraph in text.splitlines():
        words = paragraph.split()
        if not words:
            lines.append("")
            continue

        current = words[0]
        for word in words[1:]:
            candidate = current + " " + word
            if font.getlength(candidate) <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)

    return lines


def recognize_text(cv_image, lang):
    """Запускает Tesseract. OpenCV даёт BGR, поэтому переводим в RGB."""
    image_rgb = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
    text = pytesseract.image_to_string(image_rgb, lang=lang)
    return text


def compose_result(pil_image, recognized_text):
    """Дорисовывает распознанный текст белой полосой под исходной картинкой."""
    working = pil_image.copy()

    # Если картинка огромная - уменьшаем, чтобы подпись осталась читаемой
    if working.width > PREVIEW_MAX_WIDTH:
        scale = PREVIEW_MAX_WIDTH / working.width
        new_size = (PREVIEW_MAX_WIDTH, max(1, int(working.height * scale)))
        working = working.resize(new_size, Image.LANCZOS)

    text = recognized_text.strip()
    if not text:
        text = "(no text recognised)"

    font_size = max(14, working.width // 40)
    font = get_font(font_size)
    lines = wrap_text(text, font, working.width - 20)

    # Обрезаем слишком длинный текст, чтобы подпись осталась читаемой
    if len(lines) > MAX_TEXT_LINES:
        lines = lines[:MAX_TEXT_LINES]
        lines[-1] = lines[-1] + " ..."

    line_height = int(font_size * 1.45)
    strip_height = line_height * len(lines) + 20

    result = Image.new(
        "RGB",
        (working.width, working.height + strip_height),
        (255, 255, 255),
    )
    result.paste(working, (0, 0))

    draw = ImageDraw.Draw(result)
    draw.line(
        [(0, working.height), (working.width, working.height)],
        fill=(200, 200, 200),
        width=1,
    )

    y = working.height + 10
    for line in lines:
        draw.text((10, y), line, font=font, fill=(0, 0, 0))
        y += line_height

    return result


def show_pil_image(label, pil_image):
    """Показывает PIL-картинку в Label, подгоняя её под размер окна."""
    global photo

    preview = pil_image.copy()
    preview.thumbnail((PREVIEW_MAX_WIDTH, PREVIEW_MAX_HEIGHT), Image.LANCZOS)

    photo = ImageTk.PhotoImage(preview)
    label.config(image=photo, text="")


def main():
    root = tk.Tk()
    root.title("OCR Распознавание текста")
    root.geometry("1150x720")
    root.minsize(900, 600)

    lang_var = tk.StringVar(value="rus")

    # Если на Linux нет шрифта с кириллицей, предупреждаем сразу при запуске
    if find_font_path() is None:
        status_var = tk.StringVar(value="Внимание: не найден шрифт с поддержкой кириллицы")
    else:
        status_var = tk.StringVar(value="Изображение не загружено")

    # ---------- Верхняя панель ----------
    top_panel = tk.Frame(root)
    top_panel.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

    load_button = tk.Button(top_panel, text="Загрузить изображение", font=("Arial", 11))
    load_button.pack(side=tk.LEFT)

    tk.Label(top_panel, text="Язык:", font=("Arial", 11)).pack(side=tk.LEFT, padx=(20, 5))

    rus_radio = tk.Radiobutton(
        top_panel, text="Русский (rus)", variable=lang_var, value="rus", font=("Arial", 11)
    )
    rus_radio.pack(side=tk.LEFT)

    eng_radio = tk.Radiobutton(
        top_panel, text="Английский (eng)", variable=lang_var, value="eng", font=("Arial", 11)
    )
    eng_radio.pack(side=tk.LEFT, padx=(5, 0))

    status_label = tk.Label(top_panel, textvariable=status_var, font=("Arial", 10), fg="#555555")
    status_label.pack(side=tk.RIGHT)

    # ---------- Основная область: картинка слева, текст справа ----------
    content = tk.Frame(root)
    content.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
    content.columnconfigure(0, weight=3)
    content.columnconfigure(1, weight=2)
    content.rowconfigure(0, weight=1)

    image_label = tk.Label(
        content,
        text="Нажмите «Загрузить изображение»",
        bg="#f0f0f0",
        justify=tk.CENTER,
        font=("Arial", 12),
    )
    image_label.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

    text_frame = tk.Frame(content)
    text_frame.grid(row=0, column=1, sticky="nsew")
    text_frame.rowconfigure(0, weight=1)
    text_frame.columnconfigure(0, weight=1)

    text_area = tk.Text(text_frame, wrap=tk.WORD, font=("Segoe UI", 11), undo=True)
    text_area.grid(row=0, column=0, sticky="nsew")

    scrollbar = tk.Scrollbar(text_frame, command=text_area.yview)
    scrollbar.grid(row=0, column=1, sticky="ns")
    text_area.config(yscrollcommand=scrollbar.set)

    # ---------- Обработчик кнопки ----------
    def on_load():
        path = filedialog.askopenfilename(
            title="Выберите изображение",
            filetypes=[
                ("Изображения", "*.jpg *.jpeg *.png *.bmp *.tif *.tiff"),
                ("Все файлы", "*.*"),
            ],
        )
        if not path:
            return

        image = load_cv_image(path)
        if image is None:
            messagebox.showerror("Ошибка", "Не удалось открыть изображение:\n" + path)
            return

        lang = lang_var.get()

        # Старый результат убираем сразу, чтобы при ошибке не остался текст от прошлой картинки
        text_area.delete("1.0", tk.END)
        status_var.set("Идёт распознавание, подождите...")
        root.update_idletasks()

        try:
            text = recognize_text(image, lang)
        except Exception as error:
            status_var.set("Ошибка распознавания")
            messagebox.showerror("Ошибка OCR", str(error))
            return

        # Результат в консоль и в текстовое поле
        print(text)
        text_area.insert(tk.END, text)

        # Исходная картинка + распознанный текст под ней
        pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        result_image = compose_result(pil_image, text)
        show_pil_image(image_label, result_image)

        status_var.set(f"Готово. Язык: {lang}")

    load_button.config(command=on_load)

    root.mainloop()


if __name__ == "__main__":
    main()
