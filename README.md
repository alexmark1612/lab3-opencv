# lab3-opencv

Лабораторная работа №3: контурный анализ и распознавание текста (OCR).

## Состав проекта

| Файл | Назначение |
|---|---|
| `src/part1_contours_gui.py` | Контурный анализ: 8 шагов обработки и сетка 2×4 в одном окне OpenCV |
| `src/part2_ocr_gui.py` | OCR: выбор языка (rus/eng), распознанный текст рядом с исходной картинкой |
| `test_tesseract.py` | Проверка установки Tesseract и списка языков |
| `requirements.txt` | Python-зависимости (opencv-python, pytesseract, Pillow) |

## Установка на Linux (Ubuntu / Debian)

### 1. Системные пакеты

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip python3-tk \
                    libgl1 libglib2.0-0 \
                    tesseract-ocr tesseract-ocr-rus
```

* `python3-tk` — Tkinter (в Linux не всегда идёт в комплекте с Python);
* `libgl1`, `libglib2.0-0` — библиотеки, без которых OpenCV не загружается;
  на Ubuntu 24.04+ пакет может называться `libglib2.0-0t64`;
* `tesseract-ocr-rus` — русский языковой пакет (`rus.traineddata`).

Проверка, что Tesseract видит русский язык:

```bash
tesseract --list-langs
# eng
# osd
# rus
```

### 2. Клонирование репозитория

```bash
git clone https://github.com/alexmark1612/lab3-opencv.git
cd lab3-opencv
```

### 3. Виртуальное окружение и зависимости

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Проверка и запуск

```bash
python test_tesseract.py        # должна вывестись версия Tesseract и языки
python src/part1_contours_gui.py
python src/part2_ocr_gui.py
```

## Установка на Windows

```powershell
winget install UB-Mannheim.TesseractOCR
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python test_tesseract.py
```

Установщик Tesseract нужно запускать с дополнительным языком **Russian**
(или скачать `rus.traineddata` из репозитория `tesseract-ocr/tessdata_best`
в папку `tessdata`).

В коде путь к Tesseract задаётся только на Windows
(`C:\Tesseract-OCR\tesseract.exe`); на Linux используется `tesseract` из `PATH`.

Тестовые изображения можно складывать в `src/images/` — эта папка исключена
из правила игнорирования `*.png` / `*.jpg`.

## Состав изображения в part1

1. Исходное → 2. Оттенки серого → 3. Бинаризация (Оцу) → 4. Удаление шумов
→ 5. Все контуры → 6. Фильтрация (площадь ≥ 20) → 7. Приближение → 8. Рамки объектов

Подписи на плитках рисуются через Pillow (OpenCV не умеет кириллицу)
в отдельной полосе сверху, поэтому текст не пересекается с изображением.
Крупные изображения перед обработкой уменьшаются до ширины 1600 px.
Плитки 400×300 вписываются без искажения пропорций (с тёмными полями),
толщина контуров масштабируется, чтобы линии не исчезали при сжатии.
