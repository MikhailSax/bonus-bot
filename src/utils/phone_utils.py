# src/utils/phone_utils.py

def normalize_phone(phone: str) -> str:
    """
    Приводит телефон к формату 79XXXXXXXXX.
    Удаляет пробелы, +, -, (, )
    """

    # оставляем только цифры
    digits = "".join(ch for ch in phone if ch.isdigit())

    # если номер 11 цифр и начинается с 8 → заменяем 8 на 7
    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]

    # если начинается с 7 и длина 11 — ок
    if len(digits) == 11 and digits.startswith("7"):
        return digits

    # если 10 цифр → добавляем 7 в начало
    if len(digits) == 10:
        return "7" + digits

    # если всё ещё неправильно
    return None
