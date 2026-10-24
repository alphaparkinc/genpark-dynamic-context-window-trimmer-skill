import sys, json
from client import DynamicContextWindowTrimmerClient
sys.stdout.reconfigure(encoding='utf-8')

def handle_mcp():
    client = DynamicContextWindowTrimmerClient()
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print(json.dumps({"status": "ready", "skill": "genpark-dynamic-context-window-trimmer-skill"}))
        return
    req = json.loads(sys.stdin.read() or "{}")
    messages = req.get("messages", [])
    budget = req.get("max_token_budget", 512)
    res = client.trim_context_window(messages, max_token_budget=budget)
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    handle_mcp()
