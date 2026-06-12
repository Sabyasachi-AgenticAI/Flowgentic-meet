import logging
import textwrap
from livekit.agents import Agent, ChatContext, tts
from livekit.plugins import openai

logger = logging.getLogger("agent")


class GenericAgent(Agent):
    """Base class for our specialized agents to share common LLM setup and lifecycle behavior."""

    def __init__(
        self, instructions: str, chat_ctx: ChatContext = None, tts: tts.TTS = None, first_time: bool = False
    ) -> None:
        self.first_time = first_time
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

        # Dynamically switch the session's active TTS to match the active agent's voice
        if hasattr(self, "_tts") and self._tts and hasattr(self.session, "_tts"):
            self.session._tts = self._tts
            logger.info(f"Dynamically updated session TTS model to {getattr(self._tts, 'model', 'unknown')}")

        # Automatically trigger speech when an agent takes control (e.g. greets the user)
        if self.first_time:
            logger.info("First time enter: waiting for user to speak first.")
            self.first_time = False
        else:
            self.session.generate_reply()
