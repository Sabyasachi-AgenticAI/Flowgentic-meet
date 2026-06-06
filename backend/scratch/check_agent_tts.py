file_path = r"c:\Users\Sabyasachi\.antigravity\videoconference\livekit-multiagent\my-agent\.venv\Lib\site-packages\livekit\agents\voice\agent.py"
with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Search for matches of wrapped_tts
for idx, line in enumerate(lines):
    if "wrapped_tts" in line or "synthesize_node" in line or "tts_node" in line:
        print(f"--- Line {idx+1} ---")
        start = max(0, idx - 8)
        end = min(len(lines), idx + 8)
        for j in range(start, end):
            prefix = "-> " if j == idx else "   "
            print(f"{prefix}{j+1}: {lines[j].rstrip()}")
