"""
System utilities module - ASYNC VERSION
"""

import asyncio
import os
import subprocess
from typing import Optional


async def execute_command(command: str, timeout: int = 30) -> str:
    """Execute shell command"""
    try:
        proc = await asyncio.create_subprocess_shell(
            command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            output = stdout.decode().strip()
            if stderr:
                output += "\nSTDERR:\n" + stderr.decode().strip()
            return output
        except asyncio.TimeoutError:
            proc.kill()
            return "Error: Command timed out."
    except Exception as e:
        return f"Error executing command: {str(e)}"


async def read_file(filepath: str) -> str:
    """Read file content"""
    try:
        if not os.path.exists(filepath):
            return "Error: File not found."

        def _read():
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()

        return await asyncio.to_thread(_read)
    except Exception as e:
        return f"Error reading file: {str(e)}"


async def write_file(filepath: str, content: str) -> str:
    """Write content to file"""
    try:
        dir_path = os.path.dirname(filepath)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)

        def _write():
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

        await asyncio.to_thread(_write)
        return "File written successfully."
    except Exception as e:
        return f"Error writing file: {str(e)}"


async def list_files(directory: str = ".") -> str:
    """List files in directory"""
    try:
        if not os.path.exists(directory):
            return f"Error: Directory '{directory}' not found."

        files = os.listdir(directory)
        return str(files)
    except Exception as e:
        return f"Error listing files: {str(e)}"


async def file_exists(filepath: str) -> bool:
    """Check if file exists"""
    return os.path.exists(filepath)


def register_tools(registry):
    """Register system tools"""
    registry.register(
        "execute_command",
        execute_command,
        "Execute shell command. Arguments: command (str), timeout (int, optional)",
    )
    registry.register(
        "read_file", read_file, "Read file content. Arguments: filepath (str)"
    )
    registry.register(
        "write_file",
        write_file,
        "Write content to file. Arguments: filepath (str), content (str)",
    )
    registry.register(
        "list_files",
        list_files,
        "List files in directory. Arguments: directory (str, optional)",
    )
    registry.register(
        "file_exists", file_exists, "Check if file exists. Arguments: filepath (str)"
    )
