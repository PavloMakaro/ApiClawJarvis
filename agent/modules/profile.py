"""
User profile module - ASYNC VERSION
"""

import asyncio
import json
import os
from typing import Dict, Any, Optional

PROFILE_FILE = "data/profiles.json"


async def _load_profiles() -> Dict[str, Any]:
    """Load profiles from file"""
    if os.path.exists(PROFILE_FILE):
        try:

            def _read():
                with open(PROFILE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)

            return await asyncio.to_thread(_read)
        except Exception:
            return {}
    return {}


async def _save_profiles(profiles: Dict[str, Any]) -> None:
    """Save profiles to file"""
    os.makedirs("data", exist_ok=True)

    def _write():
        with open(PROFILE_FILE, "w", encoding="utf-8") as f:
            json.dump(profiles, f, indent=2, ensure_ascii=False)

    await asyncio.to_thread(_write)


async def set_profile_info(key: str, value: str, chat_id: str = None) -> str:
    """Save user profile information"""
    try:
        if not chat_id:
            return "Error: No chat_id provided."

        chat_id = str(chat_id)
        profiles = await _load_profiles()

        if chat_id not in profiles:
            profiles[chat_id] = {}

        profiles[chat_id][key] = value
        await _save_profiles(profiles)

        return f"Saved {key}: {value}"
    except Exception as e:
        return f"Error saving profile: {str(e)}"


async def get_profile_info(key: str, chat_id: str = None) -> str:
    """Get user profile information"""
    try:
        if not chat_id:
            return "Error: No chat_id provided."

        chat_id = str(chat_id)
        profiles = await _load_profiles()

        user_profile = profiles.get(chat_id, {})
        return user_profile.get(key, f"Info '{key}' not set.")
    except Exception as e:
        return f"Error getting profile: {str(e)}"


async def get_full_profile(chat_id: str = None) -> str:
    """Get full user profile"""
    try:
        if not chat_id:
            return "Error: No chat_id provided."

        chat_id = str(chat_id)
        profiles = await _load_profiles()

        profile = profiles.get(chat_id, {})
        return json.dumps(profile, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"Error getting full profile: {str(e)}"


async def delete_profile_key(key: str, chat_id: str = None) -> str:
    """Delete a profile key"""
    try:
        if not chat_id:
            return "Error: No chat_id provided."

        chat_id = str(chat_id)
        profiles = await _load_profiles()

        if chat_id in profiles and key in profiles[chat_id]:
            del profiles[chat_id][key]
            await _save_profiles(profiles)
            return f"Deleted {key}"

        return f"Key '{key}' not found"
    except Exception as e:
        return f"Error deleting key: {str(e)}"


def register_tools(registry):
    """Register profile tools"""
    registry.register(
        "set_profile_info",
        set_profile_info,
        "Save user profile info. Arguments: key (str), value (str)",
        requires_context=True,
    )
    registry.register(
        "get_profile_info",
        get_profile_info,
        "Get user profile info. Arguments: key (str)",
        requires_context=True,
    )
    registry.register(
        "get_full_profile",
        get_full_profile,
        "Get full user profile",
        requires_context=True,
    )
    registry.register(
        "delete_profile_key",
        delete_profile_key,
        "Delete profile key. Arguments: key (str)",
        requires_context=True,
    )
