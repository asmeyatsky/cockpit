"""
Domain Tests - AI Ports: Output Schema & Context Budget (5.6, 5.7)

Architectural Intent:
- Tests typed AI output validation and context window management
- Pure domain tests, no mocks needed
"""

import pytest
import json

from domain.ports.ai_ports import (
    OutputSchema,
    OutputFormat,
    ContextBudget,
    CompletionRequest,
)
from uuid import uuid4


class TestOutputSchema:
    def test_text_format_valid(self):
        schema = OutputSchema(format=OutputFormat.TEXT)
        assert schema.validate("Hello world") is True

    def test_text_format_empty_invalid(self):
        schema = OutputSchema(format=OutputFormat.TEXT)
        assert schema.validate("  ") is False

    def test_json_format_valid(self):
        schema = OutputSchema(format=OutputFormat.JSON)
        assert schema.validate('{"key": "value"}') is True

    def test_json_format_invalid(self):
        schema = OutputSchema(format=OutputFormat.JSON)
        assert schema.validate("not json") is False

    def test_json_with_required_fields(self):
        schema = OutputSchema(
            format=OutputFormat.JSON,
            required_fields=("name", "status"),
        )
        assert schema.validate('{"name": "x", "status": "ok"}') is True
        assert schema.validate('{"name": "x"}') is False

    def test_structured_format_always_valid(self):
        schema = OutputSchema(format=OutputFormat.STRUCTURED)
        assert schema.validate("anything") is True


class TestContextBudget:
    def test_default_budget(self):
        budget = ContextBudget()
        assert budget.max_tokens == 128000
        assert budget.available_for_history > 0

    def test_trim_history_within_budget(self):
        budget = ContextBudget()
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        trimmed = budget.trim_history(messages)
        assert len(trimmed) == 2

    def test_trim_history_exceeds_budget(self):
        budget = ContextBudget(max_tokens=100, system_prompt_budget=20,
                               user_input_budget=20, output_budget=20)
        # Available for history = 100 - 20 - 20 - 20 = 40
        # Each message ~50 chars / 4 = 12.5 tokens
        messages = [
            {"role": "user", "content": "A" * 200},  # 50 tokens
            {"role": "assistant", "content": "B" * 200},  # 50 tokens
            {"role": "user", "content": "C" * 80},   # 20 tokens
        ]
        trimmed = budget.trim_history(messages)
        # Should keep only the most recent messages that fit
        assert len(trimmed) < len(messages)
        # Most recent message should be preserved
        assert trimmed[-1]["content"] == "C" * 80

    def test_trim_empty_history(self):
        budget = ContextBudget()
        assert budget.trim_history([]) == []

    def test_custom_budget(self):
        budget = ContextBudget(
            max_tokens=32000,
            system_prompt_budget=1000,
            history_budget=20000,
            output_budget=2000,
        )
        assert budget.available_for_history == 32000 - 1000 - 8000 - 2000


class TestCompletionRequestWithSchema:
    def test_request_with_output_schema(self):
        schema = OutputSchema(format=OutputFormat.JSON, required_fields=("action",))
        request = CompletionRequest(
            agent_id=uuid4(),
            prompt="What should I do?",
            output_schema=schema,
        )
        assert request.output_schema is not None
        assert request.output_schema.format == OutputFormat.JSON

    def test_request_with_context_budget(self):
        budget = ContextBudget(max_tokens=64000)
        request = CompletionRequest(
            agent_id=uuid4(),
            prompt="Hello",
            context_budget=budget,
            conversation_history=[
                {"role": "user", "content": "Previous message"},
            ],
        )
        assert request.context_budget.max_tokens == 64000
        assert len(request.conversation_history) == 1
