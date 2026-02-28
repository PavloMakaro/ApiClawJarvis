import os
import re
import glob
import importlib.util
import inspect
import asyncio
import threading
import logging
import config
import sys
import traceback

logger = logging.getLogger(__name__)


class ToolRegistry:
    def __init__(self):
        self.tools = {}
        self.descriptions = []
        self.context = {}
        self.allowed_users = getattr(config, "ALLOWED_USERS", [])
        self._lock = threading.Lock()  # Thread-safe для hot-reload
        self._definitions_cache = None  # Кэш схем инструментов

    def set_global_context(self, **kwargs):
        """Set global context variables available to tools."""
        self.context.update(kwargs)

    def register(self, name, func, description, requires_context=False):
        """Register a new tool."""
        is_async = inspect.iscoroutinefunction(func)
        with self._lock:
            self.tools[name] = {
                "func": func,
                "description": description,
                "requires_context": requires_context,
                "is_async": is_async
            }
            self._definitions_cache = None  # Инвалидировать при регистрации нового инструмента

        try:
            sig = inspect.signature(func)
            internal_args = ["bot", "chat_id", "context", "job_queue", "registry", "agent_runner"]
            params = [p.name for p in sig.parameters.values() if p.name not in internal_args]
            args_desc = ", ".join(params)
        except Exception:
            args_desc = "..."

        self.descriptions.append(f"- {name}({args_desc}): {description}")

    def load_modules(self, modules_dir="modules"):
        """Load python files from modules directory."""
        if not os.path.exists(modules_dir):
            os.makedirs(modules_dir)

        for filepath in sorted(glob.glob(os.path.join(modules_dir, "*.py"))):
            module_name = os.path.basename(filepath)[:-3]
            if module_name == "__init__":
                continue

            try:
                spec = importlib.util.spec_from_file_location(module_name, filepath)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    if hasattr(module, "register_tools"):
                        module.register_tools(self)
                        logger.info(f"Loaded module: {module_name}")
                    else:
                        logger.debug(f"Skipped module (no register_tools): {module_name}")
            except Exception as e:
                logger.error(f"Error loading module {module_name}: {e}")

    def reload_modules(self):
        """Reloads all modules dynamically (thread-safe)."""
        with self._lock:
            self.tools = {}
            self.descriptions = []
            self._definitions_cache = None  # Инвалидировать кэш при перезагрузке

        # Invalidate module cache
        modules_abs = os.path.abspath("modules")
        to_remove = []
        for name, module in sys.modules.items():
            if hasattr(module, "__file__") and module.__file__:
                try:
                    if os.path.abspath(module.__file__).startswith(modules_abs):
                        to_remove.append(name)
                except Exception:
                    pass

        for name in to_remove:
            sys.modules.pop(name, None)

        logger.info("Reloading modules...")
        self.load_modules()
        return "Modules reloaded."

    def is_async(self, tool_name):
        with self._lock:
            if tool_name in self.tools:
                return self.tools[tool_name]["is_async"]
        return False

    def execute(self, tool_name, tool_context=None, **kwargs):
        """Execute a tool by name. If async, returns coroutine."""
        with self._lock:
            if tool_name not in self.tools:
                return f"Error: Tool '{tool_name}' not found."
            tool_info = self.tools[tool_name].copy()

        func = tool_info["func"]

        # Check authorization
        if tool_context and "chat_id" in tool_context:
            chat_id = str(tool_context["chat_id"])
            if self.allowed_users and chat_id not in [str(u) for u in self.allowed_users]:
                return f"Error: User {chat_id} is not authorized."

        # Merge contexts
        current_context = self.context.copy()
        if tool_context:
            current_context.update(tool_context)

        try:
            if tool_info["requires_context"]:
                for k, v in current_context.items():
                    if k not in kwargs:
                        kwargs[k] = v

            return func(**kwargs)
        except Exception as e:
            return f"Error executing tool '{tool_name}': {str(e)}"

    def get_descriptions(self):
        """Get formatted descriptions of all tools."""
        return "\n".join(self.descriptions)

    @staticmethod
    def _extract_param_descriptions(func):
        """Извлекает описания параметров из docstring."""
        descriptions = {}
        doc = func.__doc__ or ""
        in_args = False
        for line in doc.split('\n'):
            stripped = line.strip()
            if stripped.lower().startswith(('args:', 'arguments:', 'parameters:')):
                in_args = True
                continue
            if in_args:
                if stripped.lower().startswith(('returns:', 'return:', 'raises:', 'note:')) or (not stripped and in_args):
                    if not stripped:
                        continue
                    in_args = False
                    continue
                # Парсим "param_name: description" или "param_name (type): description"
                match = re.match(r'(\w+)\s*(?:\([^)]*\))?\s*[:\-]\s*(.*)', stripped)
                if match:
                    descriptions[match.group(1)] = match.group(2).strip()
        return descriptions

    def get_definitions(self):
        """Generate OpenAI-compatible tool definitions with parameter descriptions. Cached."""
        with self._lock:
            if self._definitions_cache is not None:
                return self._definitions_cache
            tools_snapshot = dict(self.tools)

        definitions = []
        internal_args = ["bot", "chat_id", "context", "job_queue", "registry", "agent_runner"]

        for name, info in tools_snapshot.items():
            func = info["func"]
            desc = info["description"]

            properties = {}
            required = []

            try:
                sig = inspect.signature(func)
                param_descs = self._extract_param_descriptions(func)

                for param_name, param in sig.parameters.items():
                    if param_name in internal_args or param_name in ["kwargs", "args"]:
                        continue

                    param_type = "string"
                    if param.annotation != inspect.Parameter.empty:
                        type_map = {
                            int: "integer",
                            float: "number",
                            bool: "boolean",
                            list: "array",
                            dict: "object",
                        }
                        param_type = type_map.get(param.annotation, "string")

                    prop = {"type": param_type}

                    # Добавить описание из docstring
                    if param_name in param_descs:
                        prop["description"] = param_descs[param_name]

                    properties[param_name] = prop

                    if param.default == inspect.Parameter.empty:
                        required.append(param_name)
            except Exception:
                pass

            definitions.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": desc,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                        "additionalProperties": False
                    }
                }
            })
        with self._lock:
            if self._definitions_cache is None:
                self._definitions_cache = definitions
        return self._definitions_cache
