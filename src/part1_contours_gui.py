import tkinter as tk
from tkinter import filedialog, messagebox

import cv2
import numpy as np

# Размер одной картинки в итоговой сетке
TILE_WIDTH = 400
TILE_HEIGHT = 300

# Минимальная площадь контура, всё что меньше - отбрасываем
MIN_AREA = 20


def load_image(path):
    """Читает картинку с диска. np.fromfile нужен для путей с русскими буквами."""
    data = np.fromfile(path, dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    return image


def make_tile(image, title):
    """Приводит картинку к размеру 400x300 и пишет сверху её название."""
    tile = cv2.resize(image, (TILE_WIDTH, TILE_HEIGHT))

    # Сначала чёрная обводка, потом белый текст - так читается на любом фоне
    cv2.putText(tile, title, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 4, cv2.LINE_AA)
    cv2.putText(tile, title, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1, cv2.LINE_AA)
    return tile


def process_image(path):
    """Прогоняет изображение через все 8 шагов и возвращает склеенную сетку 2x4."""
    image = load_image(path)
    if image is None:
        return None

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
    cv2.drawContours(step5, contours, -1, (0, 255, 0), 1)

    # Шаг 6. Фильтрация: оставляем только контуры с площадью не меньше 20 пикселей
    filtered = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area >= MIN_AREA:
            filtered.append(contour)

    step6 = np.zeros_like(image)
    cv2.drawContours(step6, filtered, -1, (0, 255, 0), 1)

    # Шаг 7. Упрощение (сглаживание) контуров через approxPolyDP
    approximated = []
    for contour in filtered:
        perimeter = cv2.arcLength(contour, True)
        epsilon = 0.02 * perimeter
        approx = cv2.approxPolyDP(contour, epsilon, True)
        approximated.append(approx)

    step7 = np.zeros_like(image)
    cv2.drawContours(step7, approximated, -1, (0, 255, 255), 1)

    # Шаг 8. Рамки (bounding box) на цветной копии исходного изображения
    step8 = image.copy()
    for contour in filtered:
        x, y, w, h = cv2.boundingRect(contour)
        cv2.rectangle(step8, (x, y), (x + w, y + h), (0, 255, 0), 2)

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
