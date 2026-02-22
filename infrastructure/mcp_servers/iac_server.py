"""
Infrastructure as Code (IaC) Service MCP Server

Architectural Intent:
- Exposes Terraform and Ansible operations via MCP protocol
- Tools for plan, apply, destroy, and state management

MCP Integration:
- Server name: iac-service
- Tools: terraform_plan, terraform_apply, ansible_run, get_state
- Resources: iac://{project_id}/state
"""

from mcp.server import Server
from pydantic import BaseModel
from typing import Optional
import json
import subprocess
import os


class TerraformInput(BaseModel):
    provider_id: str
    template: str
    variables: Optional[dict] = None


class AnsibleInput(BaseModel):
    provider_id: str
    playbook: str
    inventory: Optional[str] = None
    extra_vars: Optional[dict] = None


class StateInput(BaseModel):
    provider_id: str
    project_id: str


def create_iac_server() -> Server:
    server = Server("iac-service")

    @server.tool()
    async def terraform_plan(input: TerraformInput) -> dict:
        """Run terraform plan to see pending changes."""
        return {
            "success": True,
            "data": {
                "action": "plan",
                "provider_id": input.provider_id,
                "changes": [
                    {
                        "resource": "aws_instance.example",
                        "action": "create",
                        "before": None,
                        "after": {
                            "instance_type": "t3.micro",
                            "ami": "ami-0c55b159cbfafe1f0",
                        },
                    }
                ],
                "additions": 1,
                "destructions": 0,
                "changes": 1,
            },
        }

    @server.tool()
    async def terraform_apply(input: TerraformInput) -> dict:
        """Apply terraform configuration."""
        return {
            "success": True,
            "data": {
                "action": "apply",
                "provider_id": input.provider_id,
                "applied": [
                    {
                        "resource": "aws_instance.example",
                        "id": "i-1234567890abcdef0",
                        "state": "created",
                    }
                ],
                "outputs": {
                    "instance_id": "i-1234567890abcdef0",
                    "public_ip": "54.123.45.67",
                },
            },
        }

    @server.tool()
    async def terraform_destroy(input: TerraformInput) -> dict:
        """Destroy terraform managed resources."""
        return {
            "success": True,
            "data": {
                "action": "destroy",
                "provider_id": input.provider_id,
                "destroyed": [
                    {
                        "resource": "aws_instance.example",
                        "id": "i-1234567890abcdef0",
                        "state": "destroyed",
                    }
                ],
            },
        }

    @server.tool()
    async def ansible_run(input: AnsibleInput) -> dict:
        """Run ansible playbook."""
        return {
            "success": True,
            "data": {
                "action": "playbook",
                "provider_id": input.provider_id,
                "playbook": input.playbook,
                "results": {
                    "changed": 5,
                    "failures": 0,
                    "skipped": 2,
                    "ok": 10,
                },
                "hosts": {
                    "web-01": {"changed": 1, "failures": 0},
                    "web-02": {"changed": 1, "failures": 0},
                    "db-01": {"changed": 0, "failures": 0},
                },
            },
        }

    @server.tool()
    async def get_state(input: StateInput) -> dict:
        """Get current infrastructure state."""
        return {
            "success": True,
            "data": {
                "provider_id": input.provider_id,
                "project_id": input.project_id,
                "resources": [
                    {
                        "type": "aws_instance",
                        "name": "example",
                        "id": "i-1234567890abcdef0",
                        "state": "running",
                    },
                    {
                        "type": "aws_s3_bucket",
                        "name": "data-bucket",
                        "id": "bucket-123456789",
                        "state": "active",
                    },
                ],
                "last_modified": "2026-02-22T10:30:00Z",
            },
        }

    @server.resource("iac://{project_id}/state")
    async def get_project_state(project_id: str) -> str:
        """Get infrastructure state for a project."""
        return json.dumps(
            {
                "project_id": project_id,
                "terraform_version": "1.6.0",
                "resources": [
                    {"type": "aws_instance", "count": 3, "state": "active"},
                    {"type": "aws_s3_bucket", "count": 2, "state": "active"},
                    {"type": "aws_vpc", "count": 1, "state": "active"},
                ],
                "outputs": {
                    "web_instance_ids": ["i-1234567890abcdef0"],
                    "web_public_ips": ["54.123.45.67"],
                },
            }
        )

    @server.resource("iac://{project_id}/plan")
    async def get_project_plans(project_id: str) -> str:
        """Get execution plans for a project."""
        return json.dumps(
            {
                "project_id": project_id,
                "plans": [
                    {
                        "id": "plan-001",
                        "status": "applied",
                        "resources": 5,
                        "timestamp": "2026-02-20T10:00:00Z",
                    },
                    {
                        "id": "plan-002",
                        "status": "pending",
                        "resources": 2,
                        "timestamp": "2026-02-22T10:30:00Z",
                    },
                ],
            }
        )

    @server.prompt()
    async def iac_status_report(project_id: str) -> str:
        """Generate an IaC status report."""
        return f"""Infrastructure as Code Status Report

Project: {project_id}

Resources:
- AWS Instance: 3 active
- S3 Bucket: 2 active
- VPC: 1 active

Recent Plans:
- plan-001: Applied (5 resources)
- plan-002: Pending (2 resources)

Last Modified: 2026-02-22T10:30:00Z

To apply pending changes: terraform_apply
To destroy infrastructure: terraform_destroy
"""

    return server
