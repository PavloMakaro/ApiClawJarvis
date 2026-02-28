"""
Calculator module — безопасное вычисление математических выражений.
"""

import math
import asyncio


# Безопасные функции для eval
SAFE_MATH = {
    "abs": abs, "round": round, "min": min, "max": max,
    "sum": sum, "len": len, "int": int, "float": float,
    "pow": pow, "divmod": divmod,
    # math functions
    "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "log": math.log, "log2": math.log2, "log10": math.log10,
    "ceil": math.ceil, "floor": math.floor,
    "pi": math.pi, "e": math.e, "inf": math.inf,
    "factorial": math.factorial, "gcd": math.gcd,
    "radians": math.radians, "degrees": math.degrees,
    "asin": math.asin, "acos": math.acos, "atan": math.atan,
    "exp": math.exp, "hypot": math.hypot,
}


async def calculate(expression: str) -> str:
    """Безопасно вычислить математическое выражение.

    Args:
        expression: Математическое выражение (например '2**10 + sqrt(144)')

    Returns:
        str: Результат вычисления
    """
    try:
        # Очистка выражения
        expr = expression.strip()
        if not expr:
            return "Ошибка: пустое выражение."

        # Блокируем опасные операции
        forbidden = ["import", "exec", "eval", "open", "os.", "sys.", "__", "compile",
                      "globals", "locals", "getattr", "setattr", "delattr"]
        for word in forbidden:
            if word in expr.lower():
                return f"Ошибка: запрещённая операция '{word}'."

        # Безопасный eval
        result = eval(expr, {"__builtins__": {}}, SAFE_MATH)
        return f"{expr} = {result}"
    except ZeroDivisionError:
        return "Ошибка: деление на ноль."
    except Exception as e:
        return f"Ошибка вычисления: {str(e)}"


async def unit_convert(value: float, from_unit: str, to_unit: str) -> str:
    """Конвертировать единицы измерения.

    Args:
        value: Числовое значение
        from_unit: Исходная единица (km, m, cm, mm, mi, ft, in, kg, g, lb, oz, C, F, K)
        to_unit: Целевая единица
    """
    try:
        value = float(value)

        # Длина → метры
        length_to_m = {
            "km": 1000, "m": 1, "cm": 0.01, "mm": 0.001,
            "mi": 1609.344, "ft": 0.3048, "in": 0.0254, "yd": 0.9144,
        }

        # Масса → граммы
        mass_to_g = {
            "kg": 1000, "g": 1, "mg": 0.001,
            "lb": 453.592, "oz": 28.3495, "t": 1000000,
        }

        # Температура (спец. обработка)
        temp_units = {"C", "F", "K", "c", "f", "k"}

        from_u = from_unit.strip().lower()
        to_u = to_unit.strip().lower()

        # Температура
        if from_u in ("c", "f", "k") and to_u in ("c", "f", "k"):
            # В Цельсий
            if from_u == "c":
                celsius = value
            elif from_u == "f":
                celsius = (value - 32) * 5 / 9
            else:
                celsius = value - 273.15

            # Из Цельсия
            if to_u == "c":
                result = celsius
            elif to_u == "f":
                result = celsius * 9 / 5 + 32
            else:
                result = celsius + 273.15

            return f"{value} {from_unit} = {result:.2f} {to_unit}"

        # Длина
        if from_u in length_to_m and to_u in length_to_m:
            meters = value * length_to_m[from_u]
            result = meters / length_to_m[to_u]
            return f"{value} {from_unit} = {result:.4f} {to_unit}"

        # Масса
        if from_u in mass_to_g and to_u in mass_to_g:
            grams = value * mass_to_g[from_u]
            result = grams / mass_to_g[to_u]
            return f"{value} {from_unit} = {result:.4f} {to_unit}"

        return f"Ошибка: не знаю как конвертировать {from_unit} в {to_unit}. Поддерживаемые: km/m/cm/mm/mi/ft/in, kg/g/lb/oz, C/F/K"
    except Exception as e:
        return f"Ошибка конвертации: {str(e)}"


def register_tools(registry):
    registry.register(
        "calculate", calculate,
        "Вычислить математическое выражение. Args: expression (str — например '2**10 + sqrt(144)')."
    )
    registry.register(
        "unit_convert", unit_convert,
        "Конвертировать единицы измерения. Args: value (float), from_unit (str), to_unit (str). "
        "Поддержка: km/m/cm/mm/mi/ft/in, kg/g/lb/oz/t, C/F/K."
    )
