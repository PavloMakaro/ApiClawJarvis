import json

class ApiRenderer:
    """Minimal renderer for the API. Simply yields dict objects for SSE formatting."""

    def __init__(self, chat_id):
        self.chat_id = chat_id

    async def start(self):
        yield {"status": "started", "message": "Agent loop started"}

    async def stop(self):
        yield {"status": "stopped", "message": "Agent loop stopped"}

    async def update(self, status, content):
        yield {"status": status, "content": content}

    async def set_plan(self, plan_steps, total_steps):
        yield {"status": "plan_ready", "plan_steps": plan_steps, "total_steps": total_steps}

    async def handle_plan_step_start(self, step_id):
        yield {"status": "plan_step_start", "step_id": step_id}
