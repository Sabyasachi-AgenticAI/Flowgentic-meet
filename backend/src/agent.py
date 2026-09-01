import json
import logging
import os
import sys
import time
import uuid

from dotenv import load_dotenv
load_dotenv(".env.local")

from livekit import api
from livekit.agents import (
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    room_io,
    UserInputTranscribedEvent,
    ConversationItemAddedEvent,
)
from livekit.plugins import ai_coustics, deepgram, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from slide_presenter import SlidePresenter

# Monkey-patch Deepgram URL function to support custom speech speed
import livekit.plugins.deepgram._utils
import livekit.plugins.deepgram.tts

original_to_deepgram_url = livekit.plugins.deepgram._utils._to_deepgram_url

def patched_to_deepgram_url(opts: dict, base_url: str, *, websocket: bool) -> str:
    opts = opts.copy()
    try:
        frame = sys._getframe(1)
        for _ in range(3):
            if not frame:
                break
            tts_self = frame.f_locals.get("self")
            if tts_self and hasattr(tts_self, "speed"):
                opts["speed"] = tts_self.speed
                break
            elif tts_self and hasattr(tts_self, "_tts") and hasattr(tts_self._tts, "speed"):
                opts["speed"] = tts_self._tts.speed
                break
            frame = frame.f_back
    except Exception:
        pass

    if "speed" not in opts and opts.get("model") in ("aura-2-helios-en", "aura-2-arcas-en"):
        opts["speed"] = 1.15
        
    return original_to_deepgram_url(opts, base_url, websocket=websocket)

livekit.plugins.deepgram._utils._to_deepgram_url = patched_to_deepgram_url
livekit.plugins.deepgram.tts._to_deepgram_url = patched_to_deepgram_url

# Import modular components for use and backwards-compatibility (e.g. tests)
from agents import (
    TomAgent,
    PriyaAgent,
    AlexAgent,
    MarcusAgent,
    DianaAgent,
)
from api_helpers import (
    ensure_default_pptx_exists,
    get_pptx_summary,
    LINEAR_TEAM_ID,
    LINEAR_STATES,
    call_linear_api,
    call_devops_api,
    call_n8n_webhook,
    find_devops_work_item_by_linear_id,
    resolve_linear_issue,
    TICKETS,
    NEXT_TICKET_ID,
    call_notion_api,
    create_notion_page,
    query_notion_database,
    get_notion_page,
    append_notion_block,
)

logger = logging.getLogger("agent")


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session(agent_name="my-agent")
async def my_agent(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Ensure gtm_presentation.pptx exists before starting session
    ensure_default_pptx_exists()

    # Set up the standard Voice Pipeline (STT -> LLM -> TTS)
    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="en-US"),
        tts=deepgram.TTS(),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )
    
    # Initialize slide presenter on the session
    session.presenter = SlidePresenter(ctx.room)

    @session.on("user_input_transcribed")
    def on_user_input(ev: UserInputTranscribedEvent):
        if ev.is_final and ev.transcript.strip():
            async def send_user_msg():
                user_name = "User"
                for p in ctx.room.remote_participants.values():
                    if p.name:
                        user_name = p.name
                        break
                    elif p.identity:
                        user_name = p.identity
                        break
                
                payload = json.dumps({
                    "message": f"{user_name}: {ev.transcript}",
                    "timestamp": int(time.time() * 1000),
                    "id": str(uuid.uuid4())
                })
                try:
                    await ctx.room.local_participant.publish_data(
                        payload=payload,
                        topic="lk-chat-topic"
                    )
                except Exception as e:
                    logger.error(f"Failed to publish user transcript: {e}")

            import asyncio
            asyncio.create_task(send_user_msg())

    @session.on("conversation_item_added")
    def on_item_added(ev: ConversationItemAddedEvent):
        item = ev.item
        if getattr(item, "role", None) == "assistant" and getattr(item, "text_content", None):
            async def send_agent_msg():
                agent_name = "Agent"
                if session.current_agent:
                    cls_name = session.current_agent.__class__.__name__
                    if cls_name.endswith("Agent"):
                        agent_name = cls_name[:-5]
                    else:
                        agent_name = cls_name
                
                payload = json.dumps({
                    "message": f"{agent_name}: {item.text_content}",
                    "timestamp": int(time.time() * 1000),
                    "id": str(uuid.uuid4())
                })
                try:
                    await ctx.room.local_participant.publish_data(
                        payload=payload,
                        topic="lk-chat-topic"
                    )
                except Exception as e:
                    logger.error(f"Failed to publish agent message: {e}")

            import asyncio
            asyncio.create_task(send_agent_msg())

    # Start the session, initializing with the Chief of Staff agent (Tom)
    await session.start(
        agent=TomAgent(first_time=True),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=ai_coustics.audio_enhancement(
                    model=ai_coustics.EnhancerModel.QUAIL_VF_S
                ),
            ),
        ),
    )

    # Connect to the LiveKit room
    await ctx.connect()

    @ctx.room.on("data_received")
    def on_data_received(data_packet):
        try:
            topic = getattr(data_packet, "topic", None)
            data = getattr(data_packet, "data", b"")
            if topic == "lk-scenario-switch":
                payload = json.loads(data.decode("utf-8"))
                scenario = payload.get("scenario")
                logger.info(f"Received scenario switch request: {scenario}")
                
                async def handle_scenario_switch():
                    if scenario == "gtm_product":
                        from agents import PriyaAgent
                        logger.info("Activated GTM & Product Review scenario")
                        priya = PriyaAgent(chat_ctx=session.chat_ctx)
                        session.update_agent(priya)
                        await priya.show_linear_board()
                    elif scenario == "tech_compliance":
                        from agents import DianaAgent
                        logger.info("Activated Technical & Compliance Audit scenario")
                        diana = DianaAgent(chat_ctx=session.chat_ctx)
                        session.update_agent(diana)
                        await diana.show_compliance_dashboard()

                import asyncio
                asyncio.create_task(handle_scenario_switch())
        except Exception as e:
            logger.error(f"Error handling scenario switch data packet: {e}")


if __name__ == "__main__":
    cli.run_app(server)
