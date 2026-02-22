"""
Cockpit CLI

Architectural Intent:
- Command-line interface for Cockpit platform
- Uses Click for CLI framework
"""

import asyncio
import click
import json
import sys
from typing import Optional

from infrastructure.config.dependency_injection import get_container
from presentation.api.controllers import (
    CloudProviderController,
    ResourceController,
    AgentController,
    CostController,
)


def get_provider_controller() -> CloudProviderController:
    container = get_container()
    return CloudProviderController(
        create_provider_use_case=container.create_cloud_provider_use_case(),
        connect_provider_use_case=container.create_connect_provider_use_case(),
        get_provider_query=container.get_cloud_provider_query(),
        list_providers_query=container.list_cloud_providers_query(),
    )


def get_resource_controller() -> ResourceController:
    container = get_container()
    return ResourceController(
        create_resource_use_case=container.create_resource_use_case(),
        manage_resource_use_case=container.create_manage_resource_use_case(),
        get_resource_query=container.get_resource_query(),
        list_resources_query=container.list_resources_query(),
    )


def get_agent_controller() -> AgentController:
    container = get_container()
    return AgentController(
        create_agent_use_case=container.create_agent_use_case(),
        get_agent_query=container.get_agent_query(),
        list_agents_query=container.list_agents_query(),
    )


def get_cost_controller() -> CostController:
    container = get_container()
    return CostController(
        analyze_cost_use_case=container.create_cost_analysis_use_case()
    )


@click.group()
def cli():
    """Cockpit - Agentic Cloud Modernization Platform"""
    pass


@cli.group()
def provider():
    """Manage cloud providers"""
    pass


@provider.command("list")
def provider_list():
    """List all cloud providers"""
    controller = get_provider_controller()
    result = asyncio.run(controller.list())
    if result.success:
        providers = result.data.get("providers", [])
        if not providers:
            click.echo("No providers configured")
            return
        for p in providers:
            click.echo(
                f"{p['id']} | {p['provider_type']} | {p['name']} | {p['status']} | {p['region']}"
            )
    else:
        click.echo(f"Error: {result.error}", err=True)


@provider.command("create")
@click.option("--type", "-t", required=True, help="Provider type (aws, azure, gcp)")
@click.option("--name", "-n", required=True, help="Provider name")
@click.option("--region", "-r", required=True, help="Region")
@click.option("--account-id", help="Account ID")
def provider_create(type: str, name: str, region: str, account_id: Optional[str]):
    """Create a new cloud provider"""
    controller = get_provider_controller()
    result = asyncio.run(controller.create(type, name, region, account_id))
    if result.success:
        click.echo(f"Provider created: {result.data['id']}")
    else:
        click.echo(f"Error: {result.error}", err=True)


@provider.command("connect")
@click.argument("provider_id")
def provider_connect(provider_id: str):
    """Connect to a cloud provider"""
    controller = get_provider_controller()
    result = asyncio.run(controller.connect(provider_id))
    if result.success:
        click.echo(f"Provider connected: {provider_id}")
    else:
        click.echo(f"Error: {result.error}", err=True)


@provider.command("disconnect")
@click.argument("provider_id")
def provider_disconnect(provider_id: str):
    """Disconnect from a cloud provider"""
    controller = get_provider_controller()
    result = asyncio.run(controller.disconnect(provider_id))
    click.echo(f"Provider disconnected: {provider_id}")


@cli.group()
def resource():
    """Manage infrastructure resources"""
    pass


@resource.command("list")
@click.option("--provider-id", help="Filter by provider ID")
@click.option("--type", help="Filter by resource type")
@click.option("--state", help="Filter by state")
def resource_list(
    provider_id: Optional[str], type: Optional[str], state: Optional[str]
):
    """List all resources"""
    controller = get_resource_controller()
    result = asyncio.run(controller.list(provider_id, type, state))
    if result.success:
        resources = result.data.get("resources", [])
        if not resources:
            click.echo("No resources found")
            return
        for r in resources:
            click.echo(
                f"{r['id']} | {r['resource_type']} | {r['name']} | {r['state']} | {r['region']}"
            )
    else:
        click.echo(f"Error: {result.error}", err=True)


@resource.command("create")
@click.option("--provider-id", "-p", required=True, help="Provider ID")
@click.option("--type", "-t", required=True, help="Resource type")
@click.option("--name", "-n", required=True, help="Resource name")
@click.option("--region", "-r", required=True, help="Region")
@click.option("--config", help="JSON config")
def resource_create(
    provider_id: str, type: str, name: str, region: str, config: Optional[str]
):
    """Create a new resource"""
    controller = get_resource_controller()
    config_dict = json.loads(config) if config else {}
    result = asyncio.run(
        controller.create(provider_id, type, name, region, config_dict)
    )
    if result.success:
        click.echo(f"Resource created: {result.data['id']}")
    else:
        click.echo(f"Error: {result.error}", err=True)


@resource.command("start")
@click.argument("resource_id")
def resource_start(resource_id: str):
    """Start a resource"""
    controller = get_resource_controller()
    result = asyncio.run(controller.start(resource_id))
    if result.success:
        click.echo(f"Resource started: {resource_id}")
    else:
        click.echo(f"Error: {result.error}", err=True)


@resource.command("stop")
@click.argument("resource_id")
def resource_stop(resource_id: str):
    """Stop a resource"""
    controller = get_resource_controller()
    result = asyncio.run(controller.stop(resource_id))
    if result.success:
        click.echo(f"Resource stopped: {resource_id}")
    else:
        click.echo(f"Error: {result.error}", err=True)


@resource.command("terminate")
@click.argument("resource_id")
def resource_terminate(resource_id: str):
    """Terminate a resource"""
    controller = get_resource_controller()
    result = asyncio.run(controller.terminate(resource_id))
    if result.success:
        click.echo(f"Resource terminated: {resource_id}")
    else:
        click.echo(f"Error: {result.error}", err=True)


@cli.group()
def agent():
    """Manage AI agents"""
    pass


@agent.command("list")
def agent_list():
    """List all agents"""
    controller = get_agent_controller()
    result = asyncio.run(controller.list())
    if result.success:
        agents = result.data.get("agents", [])
        if not agents:
            click.echo("No agents configured")
            return
        for a in agents:
            click.echo(
                f"{a['id']} | {a['name']} | {a['provider']} | {a['model']} | {a['status']}"
            )
    else:
        click.echo(f"Error: {result.error}", err=True)


@agent.command("create")
@click.option("--name", "-n", required=True, help="Agent name")
@click.option("--description", "-d", required=True, help="Agent description")
@click.option(
    "--provider", "-p", required=True, help="AI provider (claude, openai, gemini)"
)
@click.option("--model", "-m", required=True, help="Model name")
@click.option("--prompt", required=True, help="System prompt")
@click.option("--max-tokens", default=4096, help="Max tokens")
@click.option("--temperature", default=0.7, help="Temperature")
def agent_create(
    name: str,
    description: str,
    provider: str,
    model: str,
    prompt: str,
    max_tokens: int,
    temperature: float,
):
    """Create a new agent"""
    controller = get_agent_controller()
    result = asyncio.run(
        controller.create(
            name, description, provider, model, prompt, max_tokens, temperature
        )
    )
    if result.success:
        click.echo(f"Agent created: {result.data['id']}")
    else:
        click.echo(f"Error: {result.error}", err=True)


@agent.command("activate")
@click.argument("agent_id")
def agent_activate(agent_id: str):
    """Activate an agent"""
    controller = get_agent_controller()
    result = asyncio.run(controller.activate(agent_id))
    click.echo(f"Agent activated: {agent_id}")


@agent.command("deactivate")
@click.argument("agent_id")
def agent_deactivate(agent_id: str):
    """Deactivate an agent"""
    controller = get_agent_controller()
    result = asyncio.run(controller.deactivate(agent_id))
    click.echo(f"Agent deactivated: {agent_id}")


@cli.group()
def cost():
    """Cost management"""
    pass


@cost.command("analyze")
@click.argument("provider_id")
def cost_analyze(provider_id: str):
    """Analyze costs for a provider"""
    controller = get_cost_controller()
    result = asyncio.run(controller.analyze(provider_id))
    if result.success:
        data = result.data
        click.echo(f"Current Month Cost: ${data['current_month_cost']['amount']}")
        click.echo(f"Forecast: ${data['monthly_forecast']['amount']}")
    else:
        click.echo(f"Error: {result.error}", err=True)


if __name__ == "__main__":
    cli()
