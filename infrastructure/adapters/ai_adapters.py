"""
AI Provider Adapters

Architectural Intent:
- Real AI provider implementations (Claude, OpenAI, Gemini)
- Implements AIProviderPort interface
- Following Rule 2: Interface-First Development

MCP Integration:
- Each adapter can be used by agent-service MCP server
- Tools: complete, stream_complete
- Resources: agent://{agent_id}/last-completion

Parallelization Strategy:
- All adapters are async, enabling concurrent multi-agent execution
- AgentExecutorAdapter supports parallel task fan-out
"""

import os
import logging
from typing import Optional
from dataclasses import dataclass

import anthropic
import openai
import google.generativeai as genai

from domain.ports.ai_ports import (
    AIProviderPort,
    CompletionRequest,
    CompletionResponse,
    TaskResult,
    AgentExecutorPort,
    ContextBudget,
)
from domain.entities.agent import Agent
from uuid import uuid4

logger = logging.getLogger(__name__)


DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-6"
DEFAULT_OPENAI_MODEL = "gpt-4o"
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"


def _build_messages(request: CompletionRequest) -> list[dict]:
    """5.7: Build message list with context window trimming."""
    messages = []
    if request.conversation_history:
        budget = request.context_budget or ContextBudget()
        messages = budget.trim_history(request.conversation_history)
    if not messages or messages[-1].get("content") != request.prompt:
        messages.append({"role": "user", "content": request.prompt})
    return messages


def _validate_output(request: CompletionRequest, content: str) -> bool:
    """5.6: Validate AI output against schema if provided."""
    if request.output_schema:
        return request.output_schema.validate(content)
    return True


class ClaudeAdapter(AIProviderPort):
    """Anthropic Claude implementation."""

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._client = anthropic.AsyncAnthropic(api_key=self._api_key)

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        model = request.model or DEFAULT_CLAUDE_MODEL
        messages = _build_messages(request)
        kwargs = {
            "model": model,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "messages": messages,
        }
        if request.system_prompt:
            kwargs["system"] = request.system_prompt

        message = await self._client.messages.create(**kwargs)
        content = message.content[0].text
        schema_valid = _validate_output(request, content)

        return CompletionResponse(
            content=content,
            tokens_used=message.usage.input_tokens + message.usage.output_tokens,
            model=message.model,
            finish_reason=message.stop_reason or "end_turn",
            schema_valid=schema_valid,
        )

    async def stream_complete(
        self, request: CompletionRequest, callback
    ) -> CompletionResponse:
        model = request.model or DEFAULT_CLAUDE_MODEL
        kwargs = {
            "model": model,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "messages": [{"role": "user", "content": request.prompt}],
        }
        if request.system_prompt:
            kwargs["system"] = request.system_prompt

        async with self._client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                callback(text)

        final_message = await stream.get_final_message()
        return CompletionResponse(
            content=final_message.content[0].text,
            tokens_used=final_message.usage.input_tokens
            + final_message.usage.output_tokens,
            model=final_message.model,
            finish_reason=final_message.stop_reason or "end_turn",
        )


class OpenAIAdapter(AIProviderPort):
    """OpenAI GPT implementation."""

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._client = openai.AsyncOpenAI(api_key=self._api_key)

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        model = request.model or DEFAULT_OPENAI_MODEL
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.extend(_build_messages(request))

        response = await self._client.chat.completions.create(
            model=model,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            messages=messages,
        )

        content = response.choices[0].message.content or ""
        schema_valid = _validate_output(request, content)

        return CompletionResponse(
            content=content,
            tokens_used=response.usage.total_tokens,
            model=response.model,
            finish_reason=response.choices[0].finish_reason or "stop",
            schema_valid=schema_valid,
        )

    async def stream_complete(
        self, request: CompletionRequest, callback
    ) -> CompletionResponse:
        model = request.model or DEFAULT_OPENAI_MODEL
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        response = await self._client.chat.completions.create(
            model=model,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            messages=messages,
            stream=True,
        )

        content = ""
        async for chunk in response:
            if chunk.choices[0].delta.content:
                text = chunk.choices[0].delta.content
                content += text
                callback(text)

        return CompletionResponse(
            content=content,
            tokens_used=0,
            model=model,
            finish_reason="stop",
        )


class GeminiAdapter(AIProviderPort):
    """Google Gemini implementation."""

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY")
        genai.configure(api_key=self._api_key)

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        model_name = request.model or DEFAULT_GEMINI_MODEL
        model = genai.GenerativeModel(
            model_name,
            system_instruction=request.system_prompt or None,
        )

        response = await model.generate_content_async(
            request.prompt,
            generation_config={
                "max_output_tokens": request.max_tokens,
                "temperature": request.temperature,
            },
        )

        content = response.text
        schema_valid = _validate_output(request, content)

        return CompletionResponse(
            content=content,
            tokens_used=0,
            model=model.model_name,
            finish_reason="stop",
            schema_valid=schema_valid,
        )

    async def stream_complete(
        self, request: CompletionRequest, callback
    ) -> CompletionResponse:
        model_name = request.model or DEFAULT_GEMINI_MODEL
        model = genai.GenerativeModel(
            model_name,
            system_instruction=request.system_prompt or None,
        )

        response = await model.generate_content_async(
            request.prompt,
            generation_config={
                "max_output_tokens": request.max_tokens,
                "temperature": request.temperature,
            },
            stream=True,
        )

        content = ""
        async for chunk in response:
            if chunk.text:
                content += chunk.text
                callback(chunk.text)

        return CompletionResponse(
            content=content,
            tokens_used=0,
            model=model.model_name,
            finish_reason="stop",
        )


class AgentExecutorAdapter(AgentExecutorPort):
    """Agent executor using AI providers."""

    def __init__(self, ai_provider: AIProviderPort):
        self._provider = ai_provider

    async def execute_task(self, agent: Agent, task: str, context: dict) -> TaskResult:
        try:
            system_prompt = f"""You are an AI agent named {agent.name}.
Description: {agent.description}

Your capabilities:
{chr(10).join(f"- {c.name}: {c.description}" for c in agent.capabilities)}

Available MCP tools: {", ".join(agent.mcp_tools) if agent.mcp_tools else "None"}

Context: {context}"""

            request = CompletionRequest(
                agent_id=agent.id,
                prompt=task,
                model=agent.config.model,
                system_prompt=system_prompt,
                max_tokens=agent.config.max_tokens,
                temperature=agent.config.temperature,
            )

            response = await self._provider.complete(request)

            return TaskResult(
                task_id=uuid4(),
                status="completed",
                result={"content": response.content, "model": response.model},
                tokens_used=response.tokens_used,
            )

        except Exception as e:
            return TaskResult(
                task_id=uuid4(),
                status="failed",
                error=str(e),
            )

    async def execute_workflow(
        self, agent: Agent, steps: list[dict], context: dict
    ) -> list[TaskResult]:
        results = []
        current_context = context

        for step in steps:
            result = await self.execute_task(agent, step["task"], current_context)
            results.append(result)

            if step.get("update_context", True) and result.result:
                current_context = {**current_context, "last_result": result.result}

        return results
