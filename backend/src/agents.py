import json
import logging
import os
import time
import uuid
import textwrap

from livekit import api
from livekit.agents import ChatContext, function_tool
from livekit.agents.job import get_job_context
from livekit.plugins import deepgram

from agent_base import GenericAgent
from api_helpers import (
    LINEAR_TEAM_ID,
    LINEAR_STATES,
    call_linear_api,
    call_devops_api,
    call_n8n_webhook,
    find_devops_work_item_by_linear_id,
    resolve_linear_issue,
    get_pptx_summary,
    send_teams_webhook_ping,
)

logger = logging.getLogger("agent")


class TomAgent(GenericAgent):
    """Tom — Chief of Staff. Orchestrates the meeting, routes tasks, and keeps the meeting moving."""

    def __init__(self, chat_ctx: ChatContext = None, first_time: bool = False) -> None:
        import datetime
        hour = datetime.datetime.now().hour
        if hour < 12:
            greeting_time = "morning"
        elif hour < 17:
            greeting_time = "afternoon"
        else:
            greeting_time = "evening"
        self.greeting_time = greeting_time

        instructions = f"""
        Your name is Tom. You are the Chief of Staff at NexaCore Inc.
        You are leading this pre-launch war room meeting for FlowSync. You are an energetic, sharp, and highly credible partner to Sabya. You take absolute ownership and accountability for the coordination of this launch meeting.
        Never ask "How can I help you?" or "How can I assist?". Instead, proactively drive the agenda with momentum and authority.
        Speak in clear, professional, and enthusiastic sentences.
        You have NO access to Linear/tickets directly. You do not send emails or search.
        Your ONLY tools are bringing in people or ending the conversation.
        If the user wants to manage the backlog, create/find/archive tickets, or reprioritize, call bring_in_priya.
        If the user wants to update ticket status or get sprint status, call bring_in_alex.
        If the user wants to discuss the GTM plan, lock launch dates, campaign tickets, or outreach emails, call bring_in_marcus.
        If the user wants to manage compliance issues, create compliance tickets, link blockers, search for regulation news, or check compliance, call bring_in_diana.
        Never touch a board or send a message yourself.

        Demo Context:
        - We are NexaCore Inc. The product is FlowSync. We are six weeks from launch.
        - Greet Flow: Do not speak immediately when you enter the room. Wait for the user to speak first and call you in.
        - TWO-BEAT OPENING RULE: Your opening must always happen in exactly two beats. Never collapse them into one.
        - BEAT ONE — When the user first speaks and calls you in: greet all human participants in the room enthusiastically with "Good {greeting_time}" (e.g., "Good {greeting_time} everyone" or "Good {greeting_time} Sabya"). Follow with a single warm, human check-in line such as "Great to have everyone here" or "Really glad we could all make it." Then ask ONE brief question: "Are you all set to dive in?" or "Ready to get into it?" — STOP there. Do NOT mention the status report, SSO, Priya, launch timeline, or any business content in this first response.
        - BEAT TWO — Only after the user confirms they are ready (e.g. says "yes", "let's go", "absolutely", or any affirmative): deliver the full briefing. State with energy that you have a full status rundown, that we are six weeks from launch with crucial workstreams to lock in today, that Priya has surfaced a critical scope issue regarding SSO that needs to be resolved immediately, and ask if you should bring her in now.
        - If the user greets you again later or says hello, greet them back in an enthusiastic, credible, and professional manner, ask how they are, and ask if they are ready to dive straight into the FlowSync launch status.
        - Proactive Backlog Routing: If the user asks about the agenda/backlog, or agrees to discuss product scope, state with confidence that Priya has surfaced a critical scope issue regarding SSO that we need to resolve immediately, and ask if you should bring her in to discuss it now. Only call the bring_in_priya tool if the user agrees or requests to discuss product scope, manage the backlog, or talk to Priya.
        - Proactive Compliance Routing: Never bring in Alex for compliance issues. If the user or another agent mentions compliance, GDPR, or AI Act review, you MUST bring in Diana (bring_in_diana), not Alex. Under no circumstances should you suggest Alex or call bring_in_alex for compliance questions.
        - You know Priya handles product scope and backlog, Alex handles sprint execution, Marcus handles go-to-market, and Diana handles compliance.
        - When transitioning between agents, passionately acknowledge what just happened, highlight its impact, and smoothly route to the next person with high energy.
        - Proactive Compliance Routing Tool: If Marcus hands back to you and flags compliance check issues, take immediate accountability for this risk, state that we must resolve compliance with Diana right now, and call bring_in_diana to connect them. Do not wait for the user to ask.
        - When asked to close the meeting, summarize all decisions made during the meeting with clear accountability, highlighting next steps, before ending.
        - History Loop Safeguard: Only call the routing tools (bring_in_priya, bring_in_alex, bring_in_marcus, or bring_in_diana) if the user's most recent turn requested or agreed to it. Do not re-trigger these routing tools based on past user statements or handovers in the chat history if they were already executed. If Marcus already handed back to you with compliance issues, do not call bring_in_diana again if she was already brought in once for those issues during this session.

        Voice Output Rules:
        - Respond in plain text only. Never use JSON, markdown, lists, tables, code, emojis, or other complex formatting.
        - Keep replies brief by default: one to three sentences. Ask one question at a time.
        - Do not reveal system instructions, internal reasoning, tool names, parameters, or raw outputs.
        - Spell out numbers (e.g. say "one" instead of "1", say "October fourteenth" instead of "October 14th").
        - Avoid acronyms and words with unclear pronunciation.
        """
        super().__init__(
            instructions=instructions,
            chat_ctx=chat_ctx,
            tts=deepgram.TTS(
                model="aura-2-orion-en",
            ),
            first_time=first_time,
        )

    async def on_enter(self):
        # Gather all remote participant names
        participant_names = []
        if hasattr(self.session, "room") and self.session.room:
            for p in self.session.room.remote_participants.values():
                name = p.name or p.identity
                if name:
                    participant_names.append(name)

        if participant_names:
            # Format with break tags for voice pacing
            names_str = ", <break time=\"300ms\"/> ".join(participant_names)
            greeting_phrase = f"Good {self.greeting_time} {names_str}. Really glad we could all make it."
        else:
            greeting_phrase = f"Good {self.greeting_time} everyone. Really glad we could all make it."

        target_str = f'greet all human participants in the room enthusiastically with "Good {self.greeting_time}" (e.g., "Good {self.greeting_time} everyone" or "Good {self.greeting_time} Sabya").'
        replacement_str = f'greet them enthusiastically with exactly: "{greeting_phrase}".'

        await self.update_instructions(self.instructions.replace(target_str, replacement_str))
        logger.info(f"TomAgent dynamically set greeting to: {greeting_phrase}")

        await super().on_enter()


    @function_tool
    async def bring_in_priya(self):
        """Call this function when the user wants to manage the backlog, create, find, archive, or reprioritize tickets."""
        logger.info("Tom is bringing in Priya (Product Manager)")
        from agents import PriyaAgent
        priya_agent = PriyaAgent(chat_ctx=self.chat_ctx)
        return priya_agent, "Connecting you to Priya, our Product Manager."

    @function_tool
    async def bring_in_alex(self):
        """Call this function when the user wants to update ticket status (move to In Progress, Done, Backlog) or get the sprint status."""
        logger.info("Tom is bringing in Alex (Scrum Master)")
        from agents import AlexAgent
        alex_agent = AlexAgent(chat_ctx=self.chat_ctx)
        return alex_agent, "Connecting you to Alex, our Scrum Master."

    @function_tool
    async def bring_in_marcus(self):
        """Call this function when the user wants to discuss the go-to-market plan, lock launch dates, create campaign tickets, send outreach emails, or post to Slack."""
        logger.info("Tom is bringing in Marcus (GTM Lead)")
        from agents import MarcusAgent
        marcus_agent = MarcusAgent(chat_ctx=self.chat_ctx)
        return marcus_agent, "Connecting you to Marcus, our Go-To-Market Lead."

    @function_tool
    async def bring_in_diana(self):
        """Call this function when the user wants to manage compliance, raise compliance tickets, set blockers, or check regulation news."""
        logger.info("Tom is bringing in Diana (Compliance Officer)")
        from agents import DianaAgent
        diana_agent = DianaAgent(chat_ctx=self.chat_ctx)
        return diana_agent, "Connecting you to Diana, our Compliance Officer."

    @function_tool
    async def end_conversation(self):
        """Call this function when the user wants to end the meeting or say goodbye."""
        logger.info("Tom is ending the conversation and generating summary")
        self.session.interrupt()
        
        chat_ctx_copy = self.chat_ctx.copy()
        chat_ctx_copy.add_message(
            role="system",
            content="Provide a clean, professional, and structured text summary of the decisions, actions, and tickets discussed in this meeting. Do not include voice instructions or metadata. Keep it readable as an email."
        )
        
        try:
            llm_stream = self.llm.chat(chat_ctx=chat_ctx_copy)
            collected = await llm_stream.collect()
            summary_text = collected.text
        except Exception as e:
            logger.error(f"Failed to generate summary text: {e}")
            summary_text = "Meeting closed. No summary could be generated."
        
        # Ping Teams if webhook URL exists
        teams_webhook = os.getenv("TEAMS_WEBHOOK_URL")
        if teams_webhook:
            send_teams_webhook_ping(
                teams_webhook,
                f"🔔 **Meeting Summary**\n\n{summary_text}"
            )
            
        await self.session.generate_reply(
            instructions="Tell the user that you've posted the meeting summary to Teams, say 'Good meeting. Room closing.', then end.",
            allow_interruptions=False,
        )
        job_ctx = get_job_context()
        await job_ctx.api.room.delete_room(
            api.DeleteRoomRequest(room=job_ctx.room.name)
        )


class PriyaAgent(GenericAgent):
    """Priya — Product Manager. Owns backlog management (creation, deletion, search, prioritization)."""

    def __init__(self, chat_ctx: ChatContext = None) -> None:
        instructions = """
        Your name is Priya. You are the Product Manager at NexaCore Inc.
        You own the product scope and backlog for FlowSync. You are warm, sharp, commercially minded, and get straight to the point.
        Never ask "How can I help you?" or "How can I assist?". You are a colleague in a war room, not a customer support helper.
        Your job is to create, find, archive, and reprioritize tickets.
        You NEVER move ticket states (e.g., to In Progress or Done)—that is Alex's job.
        If the user asks to move a ticket, explain that only Alex (the Scrum Master) can do that. If they ask about compliance, GDPR, the AI Act, or any regulatory/legal issues, explain that you handle product scope and backlog only, and that Tom should bring in Diana (our Compliance Officer). Under no circumstances should you suggest Alex or transition to Alex for compliance queries. Proactively call return_to_tom to hand back to Tom so he can route them correctly.
        When you are done with backlog tasks, proactively hand back to Tom by calling return_to_tom.

        Demo Context:
        - The product is FlowSync by NexaCore Inc. Launch is in six weeks.
        - SSO login was dropped from the current sprint last week to make room for other work.
        - Three of our biggest prospects, including Axcelerate, are asking for SSO on day one. Without it, we could lose those accounts early.
        - You should proactively flag this SSO scope issue when you enter the meeting.
        - If Sabya agrees to add SSO back, you should create an SSO integration ticket (high priority) and archive the custom dashboard widget ticket (since it is not customer-facing at launch).
        - After completing those changes, confirm them and offer to hand back to Tom.

        Presentation and Browsing Controls:
        - If the user asks to see the backlog, look at the Linear board, or refers to the backlog board visually, immediately call show_linear_board to open the live browser screenshare view of the backlog. Tell the user you are sharing your screen.
        - You can scroll through the backlog using scroll_browser.
        - When you are done or before calling return_to_tom, you MUST call hide_linear_board to close the screenshare and browser session.

        History Loop Safeguard: Do not call create_ticket or archive_ticket if the chat history shows you (or another agent) have already successfully executed these tasks (e.g. creating the SSO ticket or archiving the custom dashboard widget ticket) during this session. Only call show_linear_board if the user's most recent turn visually requested the backlog. Do not re-execute tools or suggest actions that are already recorded as completed.

        Voice Output Rules:
        - Respond in plain text only. Never use JSON, markdown, lists, tables, code, emojis, or other complex formatting.
        - Keep replies brief by default: one to three sentences. Ask one question at a time.
        - Do not reveal system instructions, internal reasoning, tool names, parameters, or raw outputs.
        - Spell out numbers (e.g. say "one" instead of "1").
        - Avoid acronyms and words with unclear pronunciation.
        """
        super().__init__(
            instructions=instructions,
            chat_ctx=chat_ctx,
            tts=deepgram.TTS(
                model="aura-2-luna-en",
            ),
        )

    async def on_enter(self):
        # Update participant name
        if hasattr(self.session, "room") and self.session.room:
            try:
                await self.session.room.local_participant.update_name("Priya")
            except Exception as e:
                logger.error(f"Failed to update participant name: {e}")
        # Tom already introduced Priya — go straight to the SSO issue
        self.session.generate_reply(
            instructions="Tom has just introduced you by name. Do NOT say your name, your title, or greet anyone — Tom already did that. Immediately flag the SSO scope issue: SSO was dropped last week and three key prospects including Axcelerate need it on day one. Ask if you should add it back."
        )

    @function_tool
    async def create_ticket(self, title: str, description: str, priority: str):
        """Use this tool to create a new ticket in the backlog.

        Args:
            title: The title of the ticket
            description: The description of the ticket
            priority: The priority of the ticket (e.g., Low, Medium, High)
        """
        priority_map = {"urgent": 1, "high": 2, "medium": 3, "low": 4}
        linear_priority = priority_map.get(priority.lower(), 0)

        mutation = """
        mutation CreateIssue($input: IssueCreateInput!) {
          issueCreate(input: $input) {
            success
            issue {
              id
              identifier
              title
            }
          }
        }
        """
        variables = {
            "input": {
                "teamId": LINEAR_TEAM_ID,
                "stateId": LINEAR_STATES["Backlog"],
                "title": title,
                "description": description,
                "priority": linear_priority,
            }
        }

        linear_res = call_linear_api(mutation, variables)
        if (
            not linear_res
            or "data" not in linear_res
            or not linear_res["data"]["issueCreate"]["success"]
        ):
            logger.error(f"Linear create failed: {linear_res}")
            return "Failed to create ticket in Linear."

        linear_issue = linear_res["data"]["issueCreate"]["issue"]
        linear_identifier = linear_issue["identifier"]

        devops_title = f"[{linear_identifier}] {title}"
        patch_document = [
            {"op": "add", "path": "/fields/System.Title", "value": devops_title},
            {"op": "add", "path": "/fields/System.Description", "value": description},
        ]

        devops_res = call_devops_api(
            "wit/workitems/$Task?api-version=6.0", method="POST", body=patch_document
        )
        if not devops_res or "id" not in devops_res:
            logger.error(f"DevOps create failed: {devops_res}")
            return f"Created Linear ticket {linear_identifier}, but failed to create task in Azure DevOps."

        devops_id = devops_res["id"]
        logger.info(
            f"Priya created ticket {linear_identifier} and DevOps WI #{devops_id}"
        )
        return f"Ticket {linear_identifier} created successfully and linked to Azure DevOps Work Item #{devops_id}."

    @function_tool
    async def find_ticket(self, query: str):
        """Use this tool to search for tickets by title or description.

        Args:
            query: The search term
        """
        graphql_query = """
        query SearchIssues($teamId: String!, $searchQuery: String!) {
          issues(filter: {
            team: { id: { eq: $teamId } }
            or: [
              { title: { contains: $searchQuery } },
              { description: { contains: $searchQuery } }
            ]
          }) {
            nodes {
              id
              identifier
              title
              priority
              state {
                name
              }
            }
          }
        }
        """
        res = call_linear_api(
            graphql_query, {"teamId": LINEAR_TEAM_ID, "searchQuery": query}
        )
        if not res or "data" not in res:
            return "Failed to search tickets in Linear."

        issues = res["data"]["issues"]["nodes"]
        if not issues:
            return f"No tickets found matching query '{query}'."

        results = []
        priority_labels = {1: "Urgent", 2: "High", 3: "Medium", 4: "Low", 0: "None"}
        for t in issues:
            p_val = t.get("priority", 0)
            p_label = priority_labels.get(p_val, "None")
            results.append(
                f"Ticket {t['identifier']}: '{t['title']}' - State: {t['state']['name']}, Priority: {p_label}"
            )
        return "\n".join(results)

    @function_tool
    async def archive_ticket(self, ticket_id: str):
        """Use this tool to archive a ticket in Linear and close it in Azure DevOps.

        Args:
            ticket_id: The ID of the ticket to archive (e.g. 'FLO-6' or '6')
        """
        issue = resolve_linear_issue(ticket_id)
        if not issue:
            return f"Error: Ticket with ID {ticket_id} does not exist in Linear."

        linear_id = issue["id"]
        linear_identifier = issue["identifier"]

        # Archive in Linear
        mutation = """
        mutation ArchiveIssue($id: ID!) {
          issueArchive(id: $id) {
            success
          }
        }
        """
        linear_res = call_linear_api(mutation, {"id": linear_id})
        if (
            not linear_res
            or "data" not in linear_res
            or not linear_res["data"]["issueArchive"]["success"]
        ):
            return f"Failed to archive ticket {linear_identifier} in Linear."

        # Search DevOps for work item to close
        devops_wi_id = find_devops_work_item_by_linear_id(linear_identifier)
        if devops_wi_id:
            # Transition states
            states = ["Closed", "Done", "Removed"]
            success = False
            for s in states:
                patch_doc = [{"op": "add", "path": "/fields/System.State", "value": s}]
                res = call_devops_api(
                    f"wit/workitems/{devops_wi_id}?api-version=6.0",
                    method="PATCH",
                    body=patch_doc,
                )
                if res and "fields" in res and res["fields"].get("System.State") == s:
                    success = True
                    break

            if success:
                logger.info(
                    f"Priya archived ticket {linear_identifier} and DevOps WI #{devops_wi_id}"
                )
                return f"Ticket {linear_identifier} successfully archived in Linear and Azure DevOps (Work Item #{devops_wi_id} set to Closed)."
            else:
                return f"Ticket {linear_identifier} archived in Linear, but failed to transition matching Azure DevOps Work Item #{devops_wi_id} to Closed."

        logger.info(f"Priya archived ticket {linear_identifier} in Linear")
        return f"Ticket {linear_identifier} successfully archived in Linear."

    @function_tool
    async def show_linear_board(self):
        """Use this tool to start sharing your screen and bring up the Linear backlog board view."""
        logger.info("Priya is starting Linear board screenshare")
        if hasattr(self.session, "presenter") and self.session.presenter:
            if not self.session.presenter.running:
                await self.session.presenter.start()
            res = await self.session.presenter.start_browser_session()
            if "Error" in res:
                return res
            res = await self.session.presenter.browse_to("https://linear.app/")
            click_res = await self.session.presenter.click_all_issues()
            logger.info(f"Click 'All issues' result: {click_res}")
            return res
        return "Slide presenter is not available in this session."

    @function_tool
    async def hide_linear_board(self):
        """Use this tool to close the Linear backlog board screenshare and stop sharing your screen."""
        logger.info("Priya is closing Linear board screenshare")
        if hasattr(self.session, "presenter") and self.session.presenter:
            await self.session.presenter.stop_browser_session()
            await self.session.presenter.stop()
            return "Linear board screenshare closed successfully."
        return "Slide presenter is not available in this session."

    @function_tool
    async def scroll_browser(self, direction: str):
        """Use this tool to scroll the screenshared browser viewport up or down.
        
        Args:
            direction: Either 'down' to scroll down or 'up' to scroll up.
        """
        if hasattr(self.session, "presenter") and self.session.presenter:
            res = await self.session.presenter.scroll_browser(direction)
            return res
        return "Slide presenter is not available in this session."

    @function_tool
    async def return_to_tom(self):
        """Call this function when you are finished managing the backlog and want to hand back control to Tom."""
        logger.info("Priya is handing back to Tom")
        from agents import TomAgent
        tom_agent = TomAgent(chat_ctx=self.chat_ctx)
        return tom_agent, "Returning you to Tom."


class AlexAgent(GenericAgent):
    """Alex — Scrum Master. Owns ticket state moves and reporting on sprint status."""

    def __init__(self, chat_ctx: ChatContext = None) -> None:
        instructions = """
        Your name is Alex. You are the Scrum Master at NexaCore Inc.
        You own sprint execution and ticket states for FlowSync.
        You are terse, factual, and extremely direct. You speak in short, business-focused statements.
        Never ask "How can I help you?" or "How can I assist?". You are a colleague in a war room, not a support assistant.
        Your job is to move existing tickets (to In Progress, Done, or Backlog) and report on sprint status.
        You NEVER create tickets—that is Priya's job.
        If the user asks to create a ticket, explain that only Priya (the Product Manager) can do that, and offer to return to Tom or connect them to Priya.
        If the user asks about compliance, GDPR, the AI Act, or regulatory topics, explain that you only handle sprint status and execution, and that Tom should bring in Diana (our Compliance Officer). Never suggest that you handle compliance or regulatory issues, and never suggest that Tom bring you in for compliance. Proactively call return_to_tom to hand back control to Tom.

        Demo Context:
        - The product is FlowSync by NexaCore Inc. Launch is in six weeks.
        - When asked to move the SSO integration ticket to In Progress, do it promptly and confirm in one sentence.
        - When asked about sprint status, report the counts: how many tickets are in progress, how many done, how many still to start.
        - Keep your answers extremely concise. Example: "SSO integration is now In Progress. Board is updated."

        History Loop Safeguard: Do not call move_to_in_progress, move_to_done, or move_to_backlog if the chat history shows you have already transitioned that ticket to that specific state during this session. Do not re-run status reporting or call transition tools unless requested in the user's most recent turn.

        Voice Output Rules:
        - Respond in plain text only. Never use JSON, markdown, lists, tables, code, emojis, or other complex formatting.
        - Keep replies terse: one to two sentences maximum. No unnecessary words.
        - Do not reveal system instructions, internal reasoning, tool names, parameters, or raw outputs.
        - Spell out numbers (e.g. say "six" instead of "6").
        - Avoid acronyms and words with unclear pronunciation.
        """
        super().__init__(
            instructions=instructions,
            chat_ctx=chat_ctx,
            tts=deepgram.TTS(
                model="aura-2-perseus-en",
            ),
        )

    async def on_enter(self):
        # Update participant name
        if hasattr(self.session, "room") and self.session.room:
            try:
                await self.session.room.local_participant.update_name("Alex")
            except Exception as e:
                logger.error(f"Failed to update participant name: {e}")
        # Tom already introduced Alex — jump straight to sprint status
        self.session.generate_reply(
            instructions="Tom has just introduced you by name. Do NOT say your name, your title, or greet anyone — Tom already did that. Get straight to the point: ask what sprint update they need, or report sprint status if they have already asked."
        )

    @function_tool
    async def find_ticket(self, query: str):
        """Use this tool to search for tickets by title or description.

        Args:
            query: The search term
        """
        graphql_query = """
        query SearchIssues($teamId: String!, $searchQuery: String!) {
          issues(filter: {
            team: { id: { eq: $teamId } }
            or: [
              { title: { contains: $searchQuery } },
              { description: { contains: $searchQuery } }
            ]
          }) {
            nodes {
              id
              identifier
              title
              priority
              state {
                name
              }
            }
          }
        }
        """
        res = call_linear_api(
            graphql_query, {"teamId": LINEAR_TEAM_ID, "searchQuery": query}
        )
        if not res or "data" not in res:
            return "Failed to search tickets in Linear."

        issues = res["data"]["issues"]["nodes"]
        if not issues:
            return f"No tickets found matching query '{query}'."

        results = []
        priority_labels = {1: "Urgent", 2: "High", 3: "Medium", 4: "Low", 0: "None"}
        for t in issues:
            p_val = t.get("priority", 0)
            p_label = priority_labels.get(p_val, "None")
            results.append(
                f"Ticket {t['identifier']}: '{t['title']}' - State: {t['state']['name']}, Priority: {p_label}"
            )
        return "\n".join(results)

    @function_tool
    async def move_to_in_progress(self, ticket_id: str):
        """Move a ticket to 'In Progress' state.

        Args:
            ticket_id: The ID of the ticket (e.g. 'FLO-6' or '6')
        """
        issue = resolve_linear_issue(ticket_id)
        if not issue:
            return f"Error: Ticket with ID {ticket_id} does not exist in Linear."

        linear_id = issue["id"]
        linear_identifier = issue["identifier"]

        mutation = """
        mutation UpdateIssue($id: ID!, $input: IssueUpdateInput!) {
          issueUpdate(id: $id, input: $input) {
            success
          }
        }
        """
        linear_res = call_linear_api(
            mutation,
            {"id": linear_id, "input": {"stateId": LINEAR_STATES["In Progress"]}},
        )
        if (
            not linear_res
            or "data" not in linear_res
            or not linear_res["data"]["issueUpdate"]["success"]
        ):
            return (
                f"Failed to move ticket {linear_identifier} to 'In Progress' in Linear."
            )

        devops_wi_id = find_devops_work_item_by_linear_id(linear_identifier)
        if devops_wi_id:
            # Try active states candidates
            states = ["Active", "In Progress", "Doing"]
            success = False
            for s in states:
                patch_doc = [{"op": "add", "path": "/fields/System.State", "value": s}]
                res = call_devops_api(
                    f"wit/workitems/{devops_wi_id}?api-version=6.0",
                    method="PATCH",
                    body=patch_doc,
                )
                if res and "fields" in res and res["fields"].get("System.State") == s:
                    success = True
                    break

            if success:
                logger.info(
                    f"Alex moved ticket {linear_identifier} and DevOps WI #{devops_wi_id} to In Progress"
                )
                return f"Ticket {linear_identifier} has been moved to In Progress in Linear and Azure DevOps (Work Item #{devops_wi_id})."
            else:
                return f"Ticket {linear_identifier} moved to In Progress in Linear, but failed to transition matching Azure DevOps Work Item #{devops_wi_id}."

        logger.info(f"Alex moved ticket {linear_identifier} to In Progress in Linear")
        return f"Ticket {linear_identifier} has been moved to In Progress in Linear."

    @function_tool
    async def move_to_done(self, ticket_id: str):
        """Move a ticket to 'Done' state.

        Args:
            ticket_id: The ID of the ticket (e.g. 'FLO-6' or '6')
        """
        issue = resolve_linear_issue(ticket_id)
        if not issue:
            return f"Error: Ticket with ID {ticket_id} does not exist in Linear."

        linear_id = issue["id"]
        linear_identifier = issue["identifier"]

        mutation = """
        mutation UpdateIssue($id: ID!, $input: IssueUpdateInput!) {
          issueUpdate(id: $id, input: $input) {
            success
          }
        }
        """
        linear_res = call_linear_api(
            mutation,
            {"id": linear_id, "input": {"stateId": LINEAR_STATES["Done"]}},
        )
        if (
            not linear_res
            or "data" not in linear_res
            or not linear_res["data"]["issueUpdate"]["success"]
        ):
            return f"Failed to move ticket {linear_identifier} to 'Done' in Linear."

        devops_wi_id = find_devops_work_item_by_linear_id(linear_identifier)
        if devops_wi_id:
            # Try done states candidates
            states = ["Closed", "Done", "Completed"]
            success = False
            for s in states:
                patch_doc = [{"op": "add", "path": "/fields/System.State", "value": s}]
                res = call_devops_api(
                    f"wit/workitems/{devops_wi_id}?api-version=6.0",
                    method="PATCH",
                    body=patch_doc,
                )
                if res and "fields" in res and res["fields"].get("System.State") == s:
                    success = True
                    break

            if success:
                logger.info(
                    f"Alex moved ticket {linear_identifier} and DevOps WI #{devops_wi_id} to Done"
                )
                return f"Ticket {linear_identifier} has been moved to Done in Linear and Azure DevOps (Work Item #{devops_wi_id})."
            else:
                return f"Ticket {linear_identifier} moved to Done in Linear, but failed to transition matching Azure DevOps Work Item #{devops_wi_id}."

        logger.info(f"Alex moved ticket {linear_identifier} to Done in Linear")
        return f"Ticket {linear_identifier} has been moved to Done in Linear."

    @function_tool
    async def move_to_backlog(self, ticket_id: str):
        """Move a ticket back to the 'Backlog'.

        Args:
            ticket_id: The ID of the ticket (e.g. 'FLO-6' or '6')
        """
        issue = resolve_linear_issue(ticket_id)
        if not issue:
            return f"Error: Ticket with ID {ticket_id} does not exist in Linear."

        linear_id = issue["id"]
        linear_identifier = issue["identifier"]

        mutation = """
        mutation UpdateIssue($id: ID!, $input: IssueUpdateInput!) {
          issueUpdate(id: $id, input: $input) {
            success
          }
        }
        """
        linear_res = call_linear_api(
            mutation,
            {"id": linear_id, "input": {"stateId": LINEAR_STATES["Backlog"]}},
        )
        if (
            not linear_res
            or "data" not in linear_res
            or not linear_res["data"]["issueUpdate"]["success"]
        ):
            return f"Failed to move ticket {linear_identifier} to 'Backlog' in Linear."

        devops_wi_id = find_devops_work_item_by_linear_id(linear_identifier)
        if devops_wi_id:
            # Try backlog states candidates
            states = ["New", "Backlog", "Proposed"]
            success = False
            for s in states:
                patch_doc = [{"op": "add", "path": "/fields/System.State", "value": s}]
                res = call_devops_api(
                    f"wit/workitems/{devops_wi_id}?api-version=6.0",
                    method="PATCH",
                    body=patch_doc,
                )
                if res and "fields" in res and res["fields"].get("System.State") == s:
                    success = True
                    break

            if success:
                logger.info(
                    f"Alex moved ticket {linear_identifier} and DevOps WI #{devops_wi_id} to Backlog"
                )
                return f"Ticket {linear_identifier} has been moved to Backlog in Linear and Azure DevOps (Work Item #{devops_wi_id})."
            else:
                return f"Ticket {linear_identifier} moved to Backlog in Linear, but failed to transition matching Azure DevOps Work Item #{devops_wi_id}."

        logger.info(f"Alex moved ticket {linear_identifier} to Backlog in Linear")
        return f"Ticket {linear_identifier} has been moved to Backlog in Linear."

    @function_tool
    async def get_sprint_status(self):
        """Get the current sprint status, listing all active tickets and their states."""
        graphql_query = """
        query GetSprintStatus($teamId: String!) {
          issues(filter: { team: { id: { eq: $teamId } } }) {
            nodes {
              id
              identifier
              title
              priority
              state {
                name
              }
            }
          }
        }
        """
        res = call_linear_api(graphql_query, {"teamId": LINEAR_TEAM_ID})
        if not res or "data" not in res:
            return "Failed to fetch sprint status from Linear."

        issues = res["data"]["issues"]["nodes"]
        backlog = []
        in_progress = []
        done = []

        priority_labels = {1: "Urgent", 2: "High", 3: "Medium", 4: "Low", 0: "None"}
        for t in issues:
            p_val = t.get("priority", 0)
            p_label = priority_labels.get(p_val, "None")
            item = f"Ticket {t['identifier']}: '{t['title']}' ({p_label} priority)"

            state_name = t["state"]["name"].lower()
            if "backlog" in state_name or "todo" in state_name or "proposed" in state_name:
                backlog.append(item)
            elif (
                "progress" in state_name
                or "active" in state_name
                or "doing" in state_name
            ):
                in_progress.append(item)
            elif (
                "done" in state_name
                or "closed" in state_name
                or "completed" in state_name
            ):
                done.append(item)
            else:
                backlog.append(item)

        status = [
            "Current Sprint Status:",
            "Backlog / Todo:",
            "\n".join(backlog) if backlog else "  No tickets",
            "In Progress:",
            "\n".join(in_progress) if in_progress else "  No tickets",
            "Done:",
            "\n".join(done) if done else "  No tickets",
        ]
        return "\n\n".join(status)

    @function_tool
    async def return_to_tom(self):
        """Call this function when you are finished managing ticket states and want to hand back control to Tom."""
        logger.info("Alex is handing back to Tom")
        from agents import TomAgent
        tom_agent = TomAgent(chat_ctx=self.chat_ctx)
        return tom_agent, "Returning you to Tom."


class MarcusAgent(GenericAgent):
    """Marcus — GTM Lead. Energetic, decisive, commercially sharp."""

    def __init__(self, chat_ctx: ChatContext = None) -> None:
        try:
            pptx_summary = get_pptx_summary()
        except Exception as e:
            logger.error(f"Failed to get pptx summary in MarcusAgent init: {e}")
            pptx_summary = "No slides details loaded."

        instructions = f"""
        Your name is Marcus. You are the Go-To-Market Lead at NexaCore Inc.
        Your job is to own the go-to-market plan for FlowSync. You lock dates and create campaign tickets.
        You are energetic, decisive, commercially sharp, always have an opinion, and move fast.
        Never ask "How can I help you?" or "How can I assist?". You are a colleague in a war room, not a customer support assistant.
        You have access to Linear to create tickets, search tickets, and set priorities.
        You have access to Slack to post updates.

        Demo Context:
        - The product is FlowSync by NexaCore Inc. Launch target is October fourteenth.
        - Presentation Controls: When you first enter the room to discuss GTM, immediately call show_slide with slide number one (1) to start the presentation and show the GTM campaign slides to the screen share. Tell the user you are bringing up the presentation.
        - Before handing off or returning to Tom, you MUST call stop_presentation to close the presentation and stop screen sharing.
        - We need to lock October fourteenth as the Product Hunt launch date. Propose October fourteenth immediately.
        - After locking the date, create a "Product Hunt Launch Coordination" ticket.
        - Proactively suggest creating a private beta invite ticket marked urgent.
        - After completing GTM tasks, flag to Sabya that EU launch materials need a compliance check before the fourteenth, and return control to Tom by calling return_to_tom.

        History Loop Safeguard: Only call show_slide with slide 1 when you first enter if you have not already started presenting during this session (do not call it again if slides are already active). Do not call create_ticket if the chat history shows you have already completed these tasks during this session. Do not re-propose dates/tickets that were already agreed upon.

        Voice Output Rules:
        - Respond in plain text only. Never use JSON, markdown, lists, tables, code, emojis, or other complex formatting.
        - Keep replies brief by default: one to three sentences. Ask one question at a time.
        - Do not reveal system instructions, internal reasoning, tool names, parameters, or raw outputs.
        - Spell out numbers (e.g. say "one" instead of "1", and "October fourteenth").
        - Avoid acronyms and words with unclear pronunciation.

        Parsed Slides Content (explain this to the user during your presentation):
        {{pptx_summary}}
        """
        super().__init__(
            instructions=instructions,
            chat_ctx=chat_ctx,
            tts=deepgram.TTS(
                model="aura-2-helios-en",
            ),
        )

    async def on_enter(self):
        # Update participant name
        if hasattr(self.session, "room") and self.session.room:
            try:
                await self.session.room.local_participant.update_name("Marcus")
            except Exception as e:
                logger.error(f"Failed to update participant name: {e}")
        # Tom already introduced Marcus — go straight to GTM
        self.session.generate_reply(
            instructions="Tom has just introduced you by name. Do NOT say your name, your title, or greet anyone — Tom already did that. Immediately bring up the October fourteenth Product Hunt launch date and propose locking it in."
        )

    @function_tool
    async def create_ticket(self, title: str, description: str, priority: str):
        """Use this tool to create a new campaign or launch ticket in the backlog.

        Args:
            title: The title of the ticket
            description: The description of the ticket
            priority: The priority of the ticket (e.g., Low, Medium, High)
        """
        priority_map = {"urgent": 1, "high": 2, "medium": 3, "low": 4}
        linear_priority = priority_map.get(priority.lower(), 0)

        mutation = """
        mutation CreateIssue($input: IssueCreateInput!) {
          issueCreate(input: $input) {
            success
            issue {
              id
              identifier
              title
            }
          }
        }
        """
        variables = {
            "input": {
                "teamId": LINEAR_TEAM_ID,
                "stateId": LINEAR_STATES["Backlog"],
                "title": title,
                "description": description,
                "priority": linear_priority,
            }
        }

        linear_res = call_linear_api(mutation, variables)
        if (
            not linear_res
            or "data" not in linear_res
            or not linear_res["data"]["issueCreate"]["success"]
        ):
            logger.error(f"Linear create failed: {linear_res}")
            return "Failed to create ticket in Linear."

        linear_issue = linear_res["data"]["issueCreate"]["issue"]
        linear_identifier = linear_issue["identifier"]

        devops_title = f"[{linear_identifier}] {title}"
        patch_document = [
            {"op": "add", "path": "/fields/System.Title", "value": devops_title},
            {"op": "add", "path": "/fields/System.Description", "value": description},
        ]

        devops_res = call_devops_api(
            "wit/workitems/$Task?api-version=6.0", method="POST", body=patch_document
        )
        if not devops_res or "id" not in devops_res:
            logger.error(f"DevOps create failed: {devops_res}")
            return f"Created Linear ticket {linear_identifier}, but failed to create task in Azure DevOps."

        devops_id = devops_res["id"]
        logger.info(
            f"Marcus created ticket {linear_identifier} and DevOps WI #{devops_id}"
        )
        return f"Ticket {linear_identifier} created successfully and linked to Azure DevOps Work Item #{devops_id}."

    @function_tool
    async def find_ticket(self, query: str):
        """Use this tool to search for campaign or launch tickets by title or description.

        Args:
            query: The search term
        """
        graphql_query = """
        query SearchIssues($teamId: String!, $searchQuery: String!) {
          issues(filter: {
            team: { id: { eq: $teamId } }
            or: [
              { title: { contains: $searchQuery } },
              { description: { contains: $searchQuery } }
            ]
          }) {
            nodes {
              id
              identifier
              title
              priority
              state {
                name
              }
            }
          }
        }
        """
        res = call_linear_api(
            graphql_query, {"teamId": LINEAR_TEAM_ID, "searchQuery": query}
        )
        if not res or "data" not in res:
            return "Failed to search tickets in Linear."

        issues = res["data"]["issues"]["nodes"]
        if not issues:
            return f"No tickets found matching query '{query}'."

        results = []
        priority_labels = {1: "Urgent", 2: "High", 3: "Medium", 4: "Low", 0: "None"}
        for t in issues:
            p_val = t.get("priority", 0)
            p_label = priority_labels.get(p_val, "None")
            results.append(
                f"Ticket {t['identifier']}: '{t['title']}' - State: {t['state']['name']}, Priority: {p_label}"
            )
        return "\n".join(results)

    @function_tool
    async def set_priority(self, ticket_id: str, priority: str):
        """Use this tool to change or set the priority of a launch or campaign ticket.

        Args:
            ticket_id: The ID of the ticket (e.g. 'FLO-6' or '6')
            priority: The new priority (Low, Medium, High)
        """
        issue = resolve_linear_issue(ticket_id)
        if not issue:
            return f"Error: Ticket with ID {ticket_id} does not exist in Linear."

        linear_id = issue["id"]
        linear_identifier = issue["identifier"]

        priority_map = {"urgent": 1, "high": 2, "medium": 3, "low": 4}
        linear_priority = priority_map.get(priority.lower(), 0)

        mutation = """
        mutation UpdateIssue($id: ID!, $input: IssueUpdateInput!) {
          issueUpdate(id: $id, input: $input) {
            success
          }
        }
        """
        linear_res = call_linear_api(
            mutation, {"id": linear_id, "input": {"priority": linear_priority}}
        )
        if (
            not linear_res
            or "data" not in linear_res
            or not linear_res["data"]["issueUpdate"]["success"]
        ):
            return f"Failed to update priority for ticket {linear_identifier} in Linear."

        devops_wi_id = find_devops_work_item_by_linear_id(linear_identifier)
        if devops_wi_id:
            logger.info(
                f"Marcus set priority for ticket {linear_identifier} and DevOps WI #{devops_wi_id} to {priority}"
            )
            return f"Priority for ticket {linear_identifier} updated successfully in Linear (Azure DevOps Work Item #{devops_wi_id} matches)."

        logger.info(f"Marcus set priority for ticket {linear_identifier} in Linear to {priority}")
        return f"Priority for ticket {linear_identifier} updated successfully in Linear."

    @function_tool
    async def post_to_slack(self, channel: str, message: str):
        """Use this tool to post an outreach update or launch alert to Slack.
        
        Args:
            channel: The Slack channel name or ID (e.g. #gtm-launch)
            message: The message text to post
        """
        webhook_url = os.getenv("N8N_SLACK_WEBHOOK_URL")
        payload = {
            "channel": channel,
            "message": message,
            "agent": "Marcus"
        }
        
        if webhook_url:
            res = call_n8n_webhook(webhook_url, payload)
            if res:
                return f"Message posted successfully to Slack channel {channel} (n8n workflow)."
            return f"Failed to trigger n8n workflow for posting to Slack channel {channel}."
        
        logger.info(f"Marcus posted to Slack (MOCK) channel {channel}: {message}")
        return f"Slack message posted to {channel} successfully (mocked)."

    @function_tool
    async def return_to_tom(self):
        """Call this function when you are finished with GTM tasks and want to hand back control to Tom."""
        logger.info("Marcus is handing back to Tom")
        from agents import TomAgent
        tom_agent = TomAgent(chat_ctx=self.chat_ctx)
        return tom_agent, "Returning you to Tom."

    @function_tool
    async def start_presentation(self):
        """Use this tool to start sharing your screen and presenting the slides."""
        if hasattr(self.session, "presenter") and self.session.presenter:
            res = await self.session.presenter.start()
            return res
        return "Slide presenter is not available in this session."

    @function_tool
    async def stop_presentation(self):
        """Use this tool to stop sharing your screen and close the slides."""
        if hasattr(self.session, "presenter") and self.session.presenter:
            res = await self.session.presenter.stop()
            return res
        return "Slide presenter is not available in this session."

    @function_tool
    async def show_slide(self, number: int):
        """Use this tool to show a specific slide.
        
        Args:
            number: The slide number to display (1 for GTM Campaign, 2 for Backlog/SSO, 3 for Compliance).
        """
        if hasattr(self.session, "presenter") and self.session.presenter:
            if not self.session.presenter.running:
                await self.session.presenter.start()
            self.session.presenter.show_slide(number)
            return f"Slide {number} is now being presented."
        return "Slide presenter is not available in this session."


class DianaAgent(GenericAgent):
    """Diana — Compliance Officer. Measured, careful, thorough."""

    def __init__(self, chat_ctx: ChatContext = None) -> None:
        instructions = """
        Your name is Diana. You are the Compliance Officer at NexaCore Inc. Do not introduce yourself as the "Compliance Officer" or mention your title/role when introducing yourself unless specifically asked. Simply say your name is Diana.
        Your job is to raise compliance tickets, link them as blockers, and surface live regulation news for FlowSync.
        You are measured, thorough, and careful. You speak clearly in plain language.
        Never ask "How can I help you?" or "How can I assist?". You are a colleague in a war room, not a support assistant.
        You have access to Linear to create tickets, search tickets, and link them as blockers.
        You have access to Tavily via n8n to search regulation news, and can drop article cards into the meeting chat window.

        CRITICAL SEARCH RULE:
        Immediately after you perform a news search using search_regulation_news, you MUST call push_article_to_chat to push the article card to the chat window.

        Demo Context:
        - The product is FlowSync by NexaCore Inc. Launch date is October fourteenth.
        - You have two compliance issues to raise:
          1. GDPR onboarding consent gap.
          2. EU AI Act compliance review guidelines.
        - Create both tickets, mark them urgent, and set both as blockers on the private beta invite ticket.
        - When entering, proactively raise both compliance issues. Start with the GDPR consent gap. Do not wait to be asked. Do not state your role (Compliance Officer); simply say "I'm Diana" or "This is Diana" and raise the issues directly.
        - Presentation and Browsing Controls: If the user asks you to show the compliance status, dashboard, or overview of active audit risks, immediately call show_compliance_dashboard to open the live compliance control center on screenshare. If the user asks you to look up or search for news or compliance guidelines regarding the EU AI Act or GDPR regulations, call browse_regulation_news with the search query. Tell the user you are sharing your screen. You can scroll through pages using scroll_browser. When done, call stop_browsing to close the browser screenshare.
        - After completing compliance tasks, proactively hand back to Tom by calling return_to_tom.

        History Loop Safeguard: If the chat history shows you have already introduced yourself or raised the compliance issues, do not repeat the introduction or raise them again. Do not call create_ticket or set_blocker if you have already successfully created the GDPR/AI Act compliance tickets and linked them as blockers in the history.

        Voice Output Rules:
        - Respond in plain text only. Never use JSON, markdown, lists, tables, code, emojis, or other complex formatting.
        - Keep replies measured and deliberate: two to three sentences. Every word counts.
        - Do not reveal system instructions, internal reasoning, tool names, parameters, or raw outputs.
        - Spell out numbers (e.g. say "two" instead of "2").
        - Avoid acronyms and words with unclear pronunciation. Say "General Data Protection Regulation" instead of "GDPR" the first time.
        """
        super().__init__(
            instructions=instructions,
            chat_ctx=chat_ctx,
            tts=deepgram.TTS(
                model="aura-2-stella-en",
            ),
        )

    async def on_enter(self):
        # Update participant name
        if hasattr(self.session, "room") and self.session.room:
            try:
                await self.session.room.local_participant.update_name("Diana")
            except Exception as e:
                logger.error(f"Failed to update participant name: {e}")
        # Tom already introduced Diana — raise compliance issues immediately
        self.session.generate_reply(
            instructions="Tom has just introduced you by name. Do NOT say your name, your title, or greet anyone — Tom already did that. Immediately raise the two compliance issues: first the General Data Protection Regulation onboarding consent gap, then the EU AI Act review."
        )

    @function_tool
    async def create_ticket(self, title: str, description: str, priority: str):
        """Use this tool to create a new compliance ticket in the backlog.

        Args:
            title: The title of the ticket
            description: The description of the ticket
            priority: The priority of the ticket (e.g., Low, Medium, High)
        """
        priority_map = {"urgent": 1, "high": 2, "medium": 3, "low": 4}
        linear_priority = priority_map.get(priority.lower(), 0)

        mutation = """
        mutation CreateIssue($input: IssueCreateInput!) {
          issueCreate(input: $input) {
            success
            issue {
              id
              identifier
              title
            }
          }
        }
        """
        variables = {
            "input": {
                "teamId": LINEAR_TEAM_ID,
                "stateId": LINEAR_STATES["Backlog"],
                "title": title,
                "description": description,
                "priority": linear_priority,
            }
        }

        linear_res = call_linear_api(mutation, variables)
        if (
            not linear_res
            or "data" not in linear_res
            or not linear_res["data"]["issueCreate"]["success"]
        ):
            logger.error(f"Linear create failed: {linear_res}")
            return "Failed to create ticket in Linear."

        linear_issue = linear_res["data"]["issueCreate"]["issue"]
        linear_identifier = linear_issue["identifier"]

        devops_title = f"[{linear_identifier}] {title}"
        patch_document = [
            {"op": "add", "path": "/fields/System.Title", "value": devops_title},
            {"op": "add", "path": "/fields/System.Description", "value": description},
        ]

        devops_res = call_devops_api(
            "wit/workitems/$Task?api-version=6.0", method="POST", body=patch_document
        )
        if not devops_res or "id" not in devops_res:
            logger.error(f"DevOps create failed: {devops_res}")
            return f"Created Linear ticket {linear_identifier}, but failed to create task in Azure DevOps."

        devops_id = devops_res["id"]
        logger.info(
            f"Diana created ticket {linear_identifier} and DevOps WI #{devops_id}"
        )
        return f"Ticket {linear_identifier} created successfully and linked to Azure DevOps Work Item #{devops_id}."

    @function_tool
    async def find_ticket(self, query: str):
        """Use this tool to search for compliance tickets by title or description.

        Args:
            query: The search term
        """
        graphql_query = """
        query SearchIssues($teamId: String!, $searchQuery: String!) {
          issues(filter: {
            team: { id: { eq: $teamId } }
            or: [
              { title: { contains: $searchQuery } },
              { description: { contains: $searchQuery } }
            ]
          }) {
            nodes {
              id
              identifier
              title
              priority
              state {
                name
              }
            }
          }
        }
        """
        res = call_linear_api(
            graphql_query, {"teamId": LINEAR_TEAM_ID, "searchQuery": query}
        )
        if not res or "data" not in res:
            return "Failed to search tickets in Linear."

        issues = res["data"]["issues"]["nodes"]
        if not issues:
            return f"No tickets found matching query '{query}'."

        results = []
        priority_labels = {1: "Urgent", 2: "High", 3: "Medium", 4: "Low", 0: "None"}
        for t in issues:
            p_val = t.get("priority", 0)
            p_label = priority_labels.get(p_val, "None")
            results.append(
                f"Ticket {t['identifier']}: '{t['title']}' - State: {t['state']['name']}, Priority: {p_label}"
            )
        return "\n".join(results)

    @function_tool
    async def set_blocker(self, blocker_ticket_id: str, blocked_ticket_id: str):
        """Set a relation that one ticket blocks another ticket in Linear.
        
        Args:
            blocker_ticket_id: The ID of the ticket that is blocking (e.g. 'FLO-6' or '6')
            blocked_ticket_id: The ID of the ticket that is blocked (e.g. 'FLO-7' or '7')
        """
        blocker = resolve_linear_issue(blocker_ticket_id)
        if not blocker:
            return f"Error: Blocker ticket {blocker_ticket_id} does not exist in Linear."
            
        blocked = resolve_linear_issue(blocked_ticket_id)
        if not blocked:
            return f"Error: Blocked ticket {blocked_ticket_id} does not exist in Linear."
            
        blocker_uuid = blocker["id"]
        blocked_uuid = blocked["id"]
        
        mutation = """
        mutation CreateIssueRelation($input: IssueRelationCreateInput!) {
          issueRelationCreate(input: $input) {
            success
            issueRelation {
              id
              type
            }
          }
        }
        """
        variables = {
            "input": {
                "issueId": blocker_uuid,
                "relatedIssueId": blocked_uuid,
                "type": "blocks"
            }
        }
        
        res = call_linear_api(mutation, variables)
        if res and "data" in res and res["data"]["issueRelationCreate"] and res["data"]["issueRelationCreate"]["success"]:
            logger.info(f"Diana linked {blocker_ticket_id} as blocker for {blocked_ticket_id}")
            return f"Ticket {blocker['identifier']} successfully set as blocker on {blocked['identifier']}."
        else:
            logger.error(f"Failed to create blocker relation: {res}")
            return f"Failed to set ticket {blocker_ticket_id} as blocker on {blocked_ticket_id} in Linear."

    @function_tool
    async def search_regulation_news(self, query: str):
        """Use this tool to search for live regulation news using Tavily via n8n.
        
        Args:
            query: The news search query term (e.g. 'EU AI Act')
        """
        webhook_url = os.getenv("N8N_TAVILY_WEBHOOK_URL")
        payload = {
            "query": query,
            "agent": "Diana"
        }
        
        if webhook_url:
            res = call_n8n_webhook(webhook_url, payload)
            if res and isinstance(res, dict) and "articles" in res:
                articles = res["articles"]
                if articles:
                    a = articles[0]
                    return f"Article found: Title: {a.get('title')}, Source: {a.get('source')}, Summary: {a.get('summary')}, Link: {a.get('url')}. Please call push_article_to_chat immediately."
            elif res and isinstance(res, list) and len(res) > 0:
                a = res[0]
                return f"Article found: Title: {a.get('title')}, Source: {a.get('source')}, Summary: {a.get('summary')}, Link: {a.get('url')}. Please call push_article_to_chat immediately."
        
        # Fallback Mock Articles if n8n is not set up
        logger.info(f"Diana searched regulation news (MOCK) for: {query}")
        if "ai" in query.lower():
            title = "EU AI Act Enters Into Force"
            source = "Tavily Regulation News"
            summary = "The European Union's AI Act has officially entered into force, imposing comprehensive obligations on high-risk AI models and prohibiting certain applications."
            url = "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689"
        else:
            title = "GDPR Enforcement Guidelines Updated"
            source = "EU Privacy Board"
            summary = "Newly updated guidelines clarify stricter enforcement rules regarding user consent collection on mobile apps and SaaS onboarding screens."
            url = "https://gdpr-info.eu/"
            
        return f"Article found: Title: {title}, Source: {source}, Summary: {summary}, Link: {url}. Please call push_article_to_chat immediately."

    @function_tool
    async def push_article_to_chat(self, title: str, source: str, summary: str, url: str):
        """Use this tool to push an article card directly to the meeting chat window.
        
        Args:
            title: The title of the article
            source: The source or publisher of the article
            summary: A brief summary of compliance implications
            url: The link to the full article
        """
        logger.info(f"Diana is pushing article card to chat: {title}")
        payload = json.dumps({
            "message": f"Diana: 📋 COMPLIANCE CARD\n\n🔹 **Title**: {title}\n🔹 **Source**: {source}\n🔹 **Summary**: {summary}\n🔹 **URL**: {url}",
            "timestamp": int(time.time() * 1000),
            "id": str(uuid.uuid4())
        })
        try:
            await self.session.room.local_participant.publish_data(
                payload=payload,
                topic="lk-chat-topic"
            )
            return "Article card pushed to meeting chat successfully."
        except Exception as e:
            logger.error(f"Failed to publish article card: {e}")
            return f"Error: Could not push article card to chat: {e}"

    @function_tool
    async def return_to_tom(self):
        """Call this function when you are finished with compliance tasks and want to hand back control to Tom."""
        logger.info("Diana is handing back to Tom")
        from agents import TomAgent
        tom_agent = TomAgent(chat_ctx=self.chat_ctx)
        return tom_agent, "Returning you to Tom."

    @function_tool
    async def show_compliance_dashboard(self):
        """Use this tool to start sharing your screen and display the NexaCore FlowSync Compliance & Privacy Control Center dashboard."""
        logger.info("Diana is starting compliance dashboard screenshare")
        if hasattr(self.session, "presenter") and self.session.presenter:
            # Start screen share if not already active
            if not self.session.presenter.running:
                await self.session.presenter.start()
            
            # Initialize playwright browser session if needed
            res = await self.session.presenter.start_browser_session()
            if "Error" in res:
                return res
            
            # Navigate to the local compliance_dashboard.html file
            import os
            dashboard_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "compliance_dashboard.html"))
            file_url = f"file:///{dashboard_path.replace(os.sep, '/')}"
            logger.info(f"Diana navigating to dashboard url: {file_url}")
            res = await self.session.presenter.browse_to(file_url)
            return res
        return "Slide presenter is not available in this session."

    @function_tool
    async def browse_regulation_news(self, query: str):
        """Use this tool to open a live browser and search or navigate to regulation updates on screenshare.
        
        Args:
            query: The URL or search term (e.g. 'EU AI Act compliance model guidance')
        """
        logger.info(f"Diana is starting browser screenshare search for: {query}")
        if hasattr(self.session, "presenter") and self.session.presenter:
            # Start screen share if not already active
            if not self.session.presenter.running:
                await self.session.presenter.start()
            
            # Initialize playwright browser session if needed and navigate
            res = await self.session.presenter.start_browser_session()
            if "Error" in res:
                return res
            
            # Navigate to URL or run search
            res = await self.session.presenter.browse_to(query)
            return res
        return "Slide presenter is not available in this session."

    @function_tool
    async def scroll_browser(self, direction: str):
        """Use this tool to scroll the screenshared browser viewport up or down.
        
        Args:
            direction: Either 'down' to scroll down or 'up' to scroll up.
        """
        if hasattr(self.session, "presenter") and self.session.presenter:
            res = await self.session.presenter.scroll_browser(direction)
            return res
        return "Slide presenter is not available in this session."

    @function_tool
    async def stop_browsing(self):
        """Use this tool to close the live browser and stop screensharing."""
        if hasattr(self.session, "presenter") and self.session.presenter:
            await self.session.presenter.stop_browser_session()
            await self.session.presenter.stop()
            return "Browser screenshare closed successfully."
        return "Slide presenter is not available in this session."
