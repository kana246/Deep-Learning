#logic.py
from item_data import items
from command_data import commands


def search_items(query, category=None):
    query = query.lower().strip()
    results = []

    for item_id, item in items.items():
        if category and category != "すべて" and item.get("category") != category:
            continue
        if query in item_id.lower():
            results.append((item_id, item))
        elif query in item["name"].lower():
            results.append((item_id, item))
        elif query in item["desc"].lower():
            results.append((item_id, item))
        elif any(query in alias.lower() for alias in item.get("aliases", [])):
            results.append((item_id, item))

    return results
    
from command_data import commands

def search_commands(query):
    query = query.lower().strip()
    results = []

    for cmd_key, cmd in commands.items():
        if query in cmd_key.lower():
            results.append((cmd_key, cmd))
        elif query in cmd["name"].lower():
            results.append((cmd_key, cmd))
        elif query in cmd["desc"].lower():
            results.append((cmd_key, cmd))
        elif any(query in alias.lower() for alias in cmd.get("aliases", [])):
            results.append((cmd_key, cmd))

    return results

def get_command_explanation(cmd, items, commands):
    parts = cmd.split()
    explain_parts = []
    for part in parts:
        if part in commands:
            explain_parts.append(commands[part]["desc"])
        elif part in items:
            explain_parts.append(items[part]["name"])
    return " / ".join(explain_parts) if explain_parts else "説明なし"

    from command_data import commands
