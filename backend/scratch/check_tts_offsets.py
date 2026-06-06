file_path = r"c:\Users\Sabyasachi\.antigravity\videoconference\livekit-multiagent\my-agent\.venv\Lib\site-packages\livekit\agents\voice\agent_session.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Let's inspect around specific offsets or line numbers.
# We will split into lines and print lines with indexes around those matches.
lines = content.splitlines()
line_nums = [794, 4151, 7606, 7622, 10168, 10173, 11779, 12206, 17895, 17918, 17956, 18078, 38305, 38932, 60848, 69115, 69128]
# Actually, the matches were character offsets, not line numbers!
# Let's print matches by splitting the content or using character offsets.
matches = [794, 4151, 7606, 7622, 10168, 10173, 11779, 12206, 17895, 17918, 17956, 18078, 38305, 38932, 60848, 69115, 69128]
for m in matches:
    start = max(0, m - 50)
    end = min(len(content), m + 50)
    print(f"Offset {m}: {repr(content[start:end])}")
