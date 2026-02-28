import sys
import os
import subprocess

def register_tools(registry):
    registry.register("install_package", install_package, "Installs a pip package. Arguments: package_name (str).")
    registry.register("restart_bot", restart_bot, "Restarts the bot application.")

def install_package(package_name):
    """Installs a python package via pip."""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        return f"Package '{package_name}' installed successfully."
    except Exception as e:
        return f"Error installing package: {str(e)}"

def restart_bot():
    """Restarts the bot process."""
    print("Restarting bot...")
    os.execv(sys.executable, [sys.executable] + sys.argv)
