"""
AI Co-pilot Service

Architectural Intent:
- Processes natural language commands from the frontend
- Executes actions via the existing use cases
- Returns structured responses for the UI
"""

import os
import json
import re
from typing import Optional
from dataclasses import dataclass

import anthropic
import openai

from infrastructure.config.dependency_injection import get_container


@dataclass
class ActionResult:
    success: bool
    message: str
    action_taken: Optional[str] = None
    data: Optional[dict] = None


class AICopilotService:
    def __init__(self):
        self._claude_client = None
        self._openai_client = None
        self._provider = os.environ.get("AI_PROVIDER", "claude")

    def _get_claude_client(self):
        if not self._claude_client:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if api_key:
                self._claude_client = anthropic.AsyncAnthropic(api_key=api_key)
        return self._claude_client

    def _get_openai_client(self):
        if not self._openai_client:
            api_key = os.environ.get("OPENAI_API_KEY")
            if api_key:
                self._openai_client = openai.AsyncOpenAI(api_key=api_key)
        return self._openai_client

    async def process_command(self, user_message: str) -> ActionResult:
        user_lower = user_message.lower()

        if any(kw in user_lower for kw in ["create", "add", "new provider"]):
            return await self._handle_create_provider(user_message)

        if any(kw in user_lower for kw in ["start", "stop", "terminate", "restart"]):
            return await self._handle_resource_action(user_message)

        if any(kw in user_lower for kw in ["cost", "spending", "budget", "expensive"]):
            return await self._handle_cost_query(user_message)

        if any(kw in user_lower for kw in ["show", "list", "get", "what"]):
            return await self._handle_query(user_message)

        if any(kw in user_lower for kw in ["help", "what can you do"]):
            return ActionResult(
                success=True,
                message="I can help you with:\n\n• Creating cloud providers (AWS, Azure, GCP)\n• Starting, stopping, or terminating resources\n• Viewing costs and budgets\n• Listing your resources and providers\n• Creating new instances\n\nJust tell me what you want to do!",
            )

        return await self._handle_intelligent_response(user_message)

    async def _handle_create_provider(self, message: str) -> ActionResult:
        provider_type = None
        if "aws" in message.lower():
            provider_type = "aws"
        elif "azure" in message.lower():
            provider_type = "azure"
        elif "gcp" in message.lower() or "google" in message.lower():
            provider_type = "gcp"

        if not provider_type:
            return ActionResult(
                success=True,
                message="Which cloud provider would you like to add?\n\n• AWS (Amazon Web Services)\n• Azure (Microsoft Azure)\n• GCP (Google Cloud Platform)\n\nJust say 'create AWS provider' or 'add Azure'!",
            )

        name_match = re.search(
            r"(?:named|called|name\s+is|for\s+)?([a-zA-Z0-9_-]+)", message
        )
        name = name_match.group(1) if name_match else f"{provider_type}-provider"

        region = "us-east-1"
        if "west" in message.lower():
            region = "us-west-2"
        elif "europe" in message.lower() or "eu" in message.lower():
            region = "eu-west-1"

        container = get_container()
        use_case = container.create_cloud_provider_use_case()
        result = await use_case.execute(
            provider_type=provider_type,
            name=name,
            region=region,
        )

        if result.success:
            return ActionResult(
                success=True,
                message=f"Successfully created {provider_type.upper()} provider '{name}' in {region}!",
                action_taken="create_provider",
                data=result.data,
            )
        return ActionResult(success=False, message=f"Failed: {result.error}")

    async def _handle_resource_action(self, message: str) -> ActionResult:
        container = get_container()

        action = None
        if "start" in message.lower():
            action = "start"
        elif "stop" in message.lower():
            action = "stop"
        elif "terminate" in message.lower() or "delete" in message.lower():
            action = "terminate"

        if not action:
            return ActionResult(
                success=True, message="What action? start, stop, or terminate?"
            )

        resource_match = re.search(
            r"(?:resource|instance|server|vm)\s+(?:named\s+)?([a-zA-Z0-9_-]+)",
            message.lower(),
        )

        if resource_match:
            resource_name = resource_match.group(1)
            list_use_case = container.list_resources_query()
            resources = await list_use_case.execute()

            matching = [
                r for r in resources if resource_name in r.get("name", "").lower()
            ]

            if matching:
                resource_id = matching[0]["id"]
                manage_use_case = container.create_manage_resource_use_case()

                if action == "start":
                    result = await manage_use_case.start(resource_id)
                elif action == "stop":
                    result = await manage_use_case.stop(resource_id)
                else:
                    result = await manage_use_case.terminate(resource_id)

                if result.success:
                    return ActionResult(
                        success=True,
                        message=f"Successfully {action}ed resource '{matching[0]['name']}'!",
                        action_taken=action,
                        data=result.data,
                    )

        return ActionResult(
            success=True,
            message=f"I understand you want to {action} a resource. Which one?\n\nSay something like 'start my web-server' or 'stop the database instance'.",
        )

    async def _handle_cost_query(self, message: str) -> ActionResult:
        container = get_container()

        providers = await container.list_cloud_providers_query().execute()

        if not providers:
            return ActionResult(
                success=True,
                message="You don't have any providers yet. Add a cloud provider first, then I can analyze your costs!",
            )

        provider_id = providers[0]["id"]
        cost_use_case = container.create_cost_analysis_use_case()
        result = await cost_use_case.execute(provider_id)

        if result.success:
            data = result.data
            cost = data.get("current_month_cost", {})
            forecast = data.get("monthly_forecast", {})

            return ActionResult(
                success=True,
                message=f"Here's your cost analysis:\n\n**Current Month**: ${cost.get('amount', '0')} {cost.get('currency', 'USD')}\n**Forecast**: ${forecast.get('amount', '0')} {forecast.get('currency', 'USD')}\n\nWould you like cost optimization recommendations?",
                action_taken="cost_analysis",
                data=data,
            )

        return ActionResult(success=False, message="Could not fetch cost data.")

    async def _handle_query(self, message: str) -> ActionResult:
        container = get_container()

        if "provider" in message.lower():
            providers = await container.list_cloud_providers_query().execute()
            if providers:
                msg = "Your cloud providers:\n\n"
                for p in providers:
                    msg += f"• **{p['name']}** ({p['provider_type']}) - {p['status']} in {p['region']}\n"
                return ActionResult(success=True, message=msg)
            return ActionResult(success=True, message="No providers configured yet.")

        if "resource" in message.lower():
            resources = await container.list_resources_query().execute()
            if resources:
                msg = "Your resources:\n\n"
                for r in resources:
                    msg += f"• **{r['name']}** ({r['resource_type']}) - {r['state']} in {r['region']}\n"
                return ActionResult(success=True, message=msg)
            return ActionResult(success=True, message="No resources found.")

        return ActionResult(
            success=True,
            message="You have providers and resources configured. What would you like to see?",
        )

    async def _handle_intelligent_response(self, message: str) -> ActionResult:
        client = (
            self._get_claude_client()
            if self._provider == "claude"
            else self._get_openai_client()
        )

        system_prompt = """You are an AI assistant for a cloud infrastructure management platform called Cockpit. 
You help users manage their AWS, Azure, and GCP resources through natural conversation.

Keep responses concise and friendly. Format with **bold** for important terms.
If you need more information, ask clear questions.
If something goes wrong, explain the issue simply."""

        try:
            if client and self._provider == "claude":
                response = await client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=500,
                    system=system_prompt,
                    messages=[{"role": "user", "content": message}],
                )
                return ActionResult(success=True, message=response.content[0].text)

            elif client and self._provider == "openai":
                response = await client.chat.completions.create(
                    model="gpt-4o",
                    max_tokens=500,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": message},
                    ],
                )
                return ActionResult(
                    success=True, message=response.choices[0].message.content
                )
        except Exception as e:
            pass

        return ActionResult(
            success=True,
            message=f'I understand you\'re asking about: "{message}"\n\nI can help with creating providers, managing resources, and viewing costs. What would you like to do?',
        )


_copilot_service: Optional[AICopilotService] = None


def get_copilot_service() -> AICopilotService:
    global _copilot_service
    if _copilot_service is None:
        _copilot_service = AICopilotService()
    return _copilot_service
