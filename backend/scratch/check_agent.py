import inspect
import livekit.agents.voice.agent as v_agent

# Print the source of Agent class inside voice/agent.py using utf-8 encoded string
source = inspect.getsource(v_agent.Agent)
print(source.encode("utf-8"))
