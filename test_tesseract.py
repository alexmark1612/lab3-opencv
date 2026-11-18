import os
import platform
import shutil

import pytesseract

# Tesseract: на Windows он у нас установлен в нестандартную папку,
# на Linux обычно лежит в PATH (/usr/bin/tesseract), поэтому путь не задаём
TESSERACT_WINDOWS_PATH = r"C:\Tesseract-OCR\tesseract.exe"

if platform.system() == "Windows" and os.path.exists(TESSERACT_WINDOWS_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_WINDOWS_PATH
else:
    tesseract_in_path = shutil.which("tesseract")
    if tesseract_in_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_in_path

print(f"ОС: {platform.system()} {platform.release()}")

try:
    version = pytesseract.get_tesseract_version()
    print(f"Tesseract установлен! Версия: {version}")
    print("Доступные языки:", ", ".join(pytesseract.get_languages(config="")))
except Exception as e:
    print("ОШИБКА: Tesseract не найден в системе. Нужно установить.")
    print(e)
