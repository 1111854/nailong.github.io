import os
import json
from datetime import datetime
from config import HISTORY_DIR

def save_conversation(messages, session_id, system_prompt):
    if not messages:
        return
    filename = os.path.join(HISTORY_DIR, f"chat_{session_id}.json")
    data = {
        "id": session_id,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "messages": messages,
        "system_prompt": system_prompt
    }
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_conversation(session_id):
    filename = os.path.join(HISTORY_DIR, f"chat_{session_id}.json")
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None

def delete_conversation(session_id):
    filename = os.path.join(HISTORY_DIR, f"chat_{session_id}.json")
    try:
        os.remove(filename)
        return True
    except:
        return False

def list_conversations():
    conversations = []
    if os.path.exists(HISTORY_DIR):
        for file in os.listdir(HISTORY_DIR):
            if file.startswith("chat_") and file.endswith(".json"):
                try:
                    with open(os.path.join(HISTORY_DIR, file), "r", encoding="utf-8") as f:
                        data = json.load(f)
                        conversations.append({
                            "id": data["id"],
                            "created_at": data["created_at"],
                            "message_count": len(data["messages"])
                        })
                except:
                    pass
    conversations.sort(key=lambda x: x["created_at"], reverse=True)
    return conversations