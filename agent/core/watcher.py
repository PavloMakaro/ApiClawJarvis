import time
import os
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)


class ModuleHandler(FileSystemEventHandler):
    def __init__(self, registry):
        self.registry = registry
        self.last_reload = 0

    def on_created(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith(".py"):
            self._trigger_reload()

    def on_modified(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith(".py"):
            self._trigger_reload()

    def on_deleted(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith(".py"):
            self._trigger_reload()

    def _trigger_reload(self):
        # Debounce (1 second)
        now = time.time()
        if now - self.last_reload < 1:
            return
        self.last_reload = now

        try:
            logger.info("File change detected. Reloading modules...")
            self.registry.reload_modules()
        except Exception as e:
            logger.error(f"Error reloading modules: {e}")


class ModuleWatcher:
    def __init__(self, registry, modules_dir="modules"):
        self.registry = registry
        self.modules_dir = modules_dir
        self.observer = Observer()

    def start(self):
        if not os.path.exists(self.modules_dir):
            os.makedirs(self.modules_dir)

        event_handler = ModuleHandler(self.registry)
        self.observer.schedule(event_handler, self.modules_dir, recursive=False)
        self.observer.start()
        logger.info(f"Started watching {self.modules_dir} for changes...")

    def stop(self):
        self.observer.stop()
        self.observer.join()
