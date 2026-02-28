import os
import sys

def register_tools(registry):
    registry.register("create_new_skill", create_new_skill, "Creates a new skill/tool by writing Python code to a file. Arguments: filename (str, e.g., 'my_tool.py'), code (str).")
    registry.register("reload_all_skills", reload_all_skills, "Reloads all skills from the modules directory.", requires_context=True)

def create_new_skill(filename, code):
    """Writes a new Python file to the modules directory."""
    if not filename.endswith(".py"):
        filename += ".py"

    filepath = os.path.join("modules", filename)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(code)
        return f"Skill created successfully at {filepath}. Call reload_all_skills to use it."
    except Exception as e:
        return f"Error creating skill: {str(e)}"

def reload_all_skills(registry=None, **kwargs):
    """Reloads the tool registry."""
    if not registry:
        return "Error: Registry context missing. Cannot reload."

    try:
        msg = registry.reload_modules()
        return f"Success: {msg}"
    except Exception as e:
        return f"Error reloading skills: {str(e)}"
