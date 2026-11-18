import tkinter as tk
from tkinter import filedialog, messagebox

import cv2
import numpy as np

# Размер одной картинки в итоговой сетке
TILE_WIDTH = 400
TILE_HEIGHT = 300

# Минимальная площадь контура, всё что меньше - отбрасываем
MIN_AREA = 20

# Максимальная ширина изображения для обработки.
# Большие фото уменьшаем сразу: и память экономим, и контуры после
# сжатия в плитку 400x300 остаются видимыми
MAX_IMAGE_WIDTH = 1600


def load_image(path):
    """Читает картинку с диска. np.fromfile нужен для путей с русскими буквами."""
    data = np.fromfile(path, dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)

    if image is not None and image.shape[1] > MAX_IMAGE_WIDTH:
        scale = MAX_IMAGE_WIDTH / image.shape[1]
        new_size = (MAX_IMAGE_WIDTH, max(1, int(round(image.shape[0] * scale))))
        image = cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)
        print(f"Изображение уменьшено до {new_size[0]}x{new_size[1]}")

    return image


def make_tile(image, title):
    """Вписывает картинку в плитку 400x300 без искажения пропорций и подписывает её."""
    height, width = image.shape[:2]
    scale = min(TILE_WIDTH / width, TILE_HEIGHT / height)

    new_width = max(1, int(round(width * scale)))
    new_height = max(1, int(round(height * scale)))
    interpolation = cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR
    resized = cv2.resize(image, (new_width, new_height), interpolation=interpolation)

    # Тёмный фон, чтобы плитка всегда была ровно 400x300
    tile = np.full((TILE_HEIGHT, TILE_WIDTH, 3), 40, np.uint8)
    x = (TILE_WIDTH - new_width) // 2
    y = (TILE_HEIGHT - new_height) // 2
    tile[y:y + new_height, x:x + new_width] = resized

    # Сначала чёрная обводка, потом белый текст - так читается на любом фоне
    cv2.putText(tile, title, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 4, cv2.LINE_AA)
    cv2.putText(tile, title, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1, cv2.LINE_AA)
    return tile


def process_image(path):
    """Прогоняет изображение через все 8 шагов и возвращает склеенную сетку 2x4."""
    image = load_image(path)
    if image is None:
        return None

    # Толщина линий с запасом, чтобы после уменьшения в плитку они не исчезали
    line_thickness = max(1, int(round(image.shape[1] / TILE_WIDTH)))

    # Шаг 1. Исходное изображение
    step1 = image.copy()

    # Шаг 2. Оттенки серого
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    step2 = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    # Шаг 3. Бинаризация методом Оцу
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    step3 = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)

    # Шаг 4. Удаление шумов: морфологическое открытие (сначала эрозия, потом дилатация)
    kernel = np.ones((3, 3), np.uint8)
    opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
    step4 = cv2.cvtColor(opened, cv2.COLOR_GRAY2BGR)

    # Шаг 5. Поиск контуров и отрисовка ВСЕХ найденных контуров на чёрном фоне
    contours, hierarchy = cv2.findContours(opened, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    step5 = np.zeros_like(image)
    cv2.drawContours(step5, contours, -1, (0, 255, 0), line_thickness)

    # Шаг 6. Фильтрация: оставляем только контуры с площадью не меньше 20 пикселей
    # Заодно запоминаем внешние контуры (у них нет родителя в hierarchy) -
    # рамки на шаге 8 рисуем только по ним, иначе внутри букв появляются лишние рамки
    filtered = []
    external = []
    for index, contour in enumerate(contours):
        area = cv2.contourArea(contour)
        if area < MIN_AREA:
            continue
        filtered.append(contour)
        if hierarchy[0][index][3] == -1:
            external.append(contour)

    step6 = np.zeros_like(image)
    cv2.drawContours(step6, filtered, -1, (0, 255, 0), line_thickness)

    # Шаг 7. Упрощение (сглаживание) контуров через approxPolyDP
    approximated = []
    for contour in filtered:
        perimeter = cv2.arcLength(contour, True)
        epsilon = 0.02 * perimeter
        approx = cv2.approxPolyDP(contour, epsilon, True)
        approximated.append(approx)

    step7 = np.zeros_like(image)
    cv2.drawContours(step7, approximated, -1, (0, 255, 255), line_thickness)

    # Шаг 8. Рамки (bounding box) на цветной копии исходного изображения
    step8 = image.copy()
    for contour in external:
        x, y, w, h = cv2.boundingRect(contour)
        cv2.rectangle(step8, (x, y), (x + w, y + h), (0, 255, 0), line_thickness)

    # Подписываем все 8 картинок
    tiles = [
        make_tile(step1, "1. Original"),
        make_tile(step2, "2. Gray"),
        make_tile(step3, "3. Binary Otsu"),
        make_tile(step4, "4. Opened"),
        make_tile(step5, "5. All contours"),
        make_tile(step6, "6. Filtered"),
        make_tile(step7, "7. Approximated"),
        make_tile(step8, "8. Bounding boxes"),
    ]

    # Сетка 2 ряда по 4 картинки
    top_row = np.hstack(tiles[0:4])
    bottom_row = np.hstack(tiles[4:8])
    grid = np.vstack([top_row, bottom_row])

    print("Найдено контуров всего:", len(contours))
    print("Осталось после фильтрации (площадь >= 20):", len(filtered))
    print("Из них внешних (для рамок):", len(external))
    return grid


def choose_file():
    """Открывает диалог выбора файла и запускает обработку."""
    path = filedialog.askopenfilename(
        title="Выберите изображение",
        filetypes=[
            ("Изображения", "*.jpg *.jpeg *.png *.bmp *.tif *.tiff"),
            ("Все файлы", "*.*"),
        ],
    )
    if not path:
        return

    grid = process_image(path)
    if grid is None:
        messagebox.showerror("Ошибка", "Не удалось открыть изображение:\n" + path)
        return

    # На Linux с GTK-сборкой OpenCV отдельный поток окна убирает зависания
    cv2.startWindowThread()
    cv2.namedWindow("Contour analysis", cv2.WINDOW_NORMAL)
    cv2.imshow("Contour analysis", grid)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def main():
    root = tk.Tk()
    root.title("Laboratory 3 - Contours")
    root.geometry("320x120")
    root.resizable(False, False)

    button = tk.Button(root, text="Загрузить изображение", font=("Arial", 12), command=choose_file)
    button.pack(expand=True)

    root.mainloop()


if __name__ == "__main__":
    main()
