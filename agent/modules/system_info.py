"""
System info module — информация о системе, процессах, диске.
"""

import os
import platform
import asyncio


async def get_system_info() -> str:
    """Получить информацию о системе (ОС, Python, диск, RAM).

    Returns:
        str: Информация о системе
    """
    try:
        info = []
        info.append(f"🖥 *Система:*")
        info.append(f"• ОС: {platform.system()} {platform.release()}")
        info.append(f"• Архитектура: {platform.machine()}")
        info.append(f"• Python: {platform.python_version()}")
        info.append(f"• Hostname: {platform.node()}")

        # Disk usage
        try:
            import shutil
            total, used, free = shutil.disk_usage("/")
            info.append(f"\n💾 *Диск:*")
            info.append(f"• Всего: {total // (1024**3)} GB")
            info.append(f"• Использовано: {used // (1024**3)} GB ({used * 100 // total}%)")
            info.append(f"• Свободно: {free // (1024**3)} GB")
        except Exception:
            pass

        # CPU count
        cpu_count = os.cpu_count()
        if cpu_count:
            info.append(f"\n⚙️ *CPU:* {cpu_count} ядер")

        # Working directory
        info.append(f"\n📂 *Рабочая директория:* {os.getcwd()}")

        return "\n".join(info)
    except Exception as e:
        return f"Ошибка: {str(e)}"


async def get_bot_status(chat_id=None, **kwargs) -> str:
    """Получить статус бота: модули, uptime, количество инструментов.

    Returns:
        str: Статус бота
    """
    try:
        import glob

        modules = glob.glob("modules/*.py")
        module_names = [os.path.basename(m)[:-3] for m in modules if not m.endswith("__init__.py")]

        info = [
            f"🤖 *Статус JarvisClaw:*",
            f"• Модулей: {len(module_names)}",
            f"• Файлы модулей: {', '.join(sorted(module_names))}",
        ]

        # Data files
        data_files = glob.glob("data/*")
        if data_files:
            info.append(f"• Файлов данных: {len(data_files)}")

        # Memory file
        mem_path = os.path.join("Permanent memory", "Permanent-memory")
        if os.path.exists(mem_path):
            size = os.path.getsize(mem_path)
            lines = 0
            with open(mem_path, "r", encoding="utf-8") as f:
                lines = sum(1 for _ in f)
            info.append(f"• Память: {lines} записей ({size} байт)")

        return "\n".join(info)
    except Exception as e:
        return f"Ошибка: {str(e)}"


def register_tools(registry):
    registry.register(
        "get_system_info", get_system_info,
        "Информация о системе (ОС, Python, диск, CPU)."
    )
    registry.register(
        "get_bot_status", get_bot_status,
        "Статус бота: модули, данные, память.",
        requires_context=True
    )
