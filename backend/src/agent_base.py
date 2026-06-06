import logging
import textwrap
from livekit.agents import Agent, ChatContext
from livekit.plugins import cartesia, openai

logger = logging.getLogger("agent")


class GenericAgent(Agent):
    """Base class for our specialized agents to share common LLM setup and lifecycle behavior."""

    def __init__(
        self, instructions: str, chat_ctx: ChatContext = None, tts: cartesia.TTS = None
    ) -> None:
        super().__init__(
            llm=openai.LLM(model="gpt-4o"),
            instructions=textwrap.dedent(instructions),
            chat_ctx=chat_ctx,
            tts=tts,
        )

    async def on_enter(self):
        # Update participant name dynamically to match the active agent
        agent_name = self.__class__.__name__
        if agent_name.endswith("Agent"):
            agent_name = agent_name[:-5]
        
        if hasattr(self.session, "room") and self.session.room:
            try:
                await self.session.room.local_participant.update_name(agent_name)
                logger.info(f"Updated local participant name to: {agent_name}")
            except Exception as e:
                logger.error(f"Failed to update participant name: {e}")

        # Automatically trigger speech when an agent takes control (e.g. greets the user)
        self.session.generate_reply()
