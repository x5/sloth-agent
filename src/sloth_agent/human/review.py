"""Human Review - Async approval via Feishu/Email."""

import json
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

import httpx

from sloth_agent.core.config import Config
from sloth_agent.core.state import PlanContext

logger = logging.getLogger("approval")


class ApprovalRequest:
    """Represents an approval request."""

    def __init__(
        self,
        request_id: str,
        plan_id: str,
        summary: str,
        tasks: list[dict],
        requested_at: str,
    ):
        self.request_id = request_id
        self.plan_id = plan_id
        self.summary = summary
        self.tasks = tasks
        self.requested_at = requested_at


class ApprovalClient:
    """Sends approval requests to humans via configured channels."""

    def __init__(self, config: Config):
        self.config = config

    def send_plan_for_approval(self, plan: PlanContext) -> bool:
        """Send plan to all configured approval channels."""
        request = ApprovalRequest(
            request_id=f"approval-{plan.plan_id}",
            plan_id=plan.plan_id,
            summary=f"Daily Plan for {plan.date}",
            tasks=[
                {
                    "id": t.task_id,
                    "description": t.description,
                    "tools": t.tools_needed,
                }
                for t in plan.tasks
            ],
            requested_at=plan.created_at.isoformat(),
        )

        success = True

        for channel in self.config.approval.async_channels:
            try:
                if channel.type == "feishu":
                    self._send_feishu(request)
                elif channel.type == "email":
                    self._send_email(request)
            except Exception as e:
                logger.error(f"Failed to send approval request via {channel.type}: {e}")
                success = False

        return success

    def _send_feishu(self, request: ApprovalRequest):
        """Send approval request via Feishu webhook."""
        webhook = self.config.approval.async_channels[0].webhook

        message = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": "Daily Plan Approval"},
                    "template": "blue",
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"**Date:** {request.summary}\n**Request ID:** {request.request_id}",
                        },
                    },
                    {"tag": "hr"},
                ],
            },
        }

        # Add task list
        for task in request.tasks:
            message["card"]["elements"].append(
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**{task['id']}**: {task['description']}\n  Tools: {', '.join(task['tools'])}",
                    },
                }
            )

        # Add approve/reject buttons
        message["card"]["elements"].extend(
            [
                {"tag": "hr"},
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "Approve"},
                            "type": "primary",
                            "action_id": "approve",
                        },
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "Reject"},
                            "type": "danger",
                            "action_id": "reject",
                        },
                    ],
                },
            ]
        )

        with httpx.Client() as client:
            response = client.post(webhook, json=message)
            response.raise_for_status()

        logger.info(f"Sent Feishu approval request: {request.request_id}")

    def _send_email(self, request: ApprovalRequest):
        """Send approval request via email."""
        channel = None
        for ch in self.config.approval.async_channels:
            if ch.type == "email":
                channel = ch
                break

        if not channel:
            return

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Daily Plan Approval - {request.summary}"
        msg["From"] = channel.from_addr
        msg["To"] = ", ".join(channel.to)

        # Plain text version
        text_content = f"""
Daily Plan Approval Required

Date: {request.summary}
Request ID: {request.request_id}

Tasks:
"""
        for task in request.tasks:
            text_content += f"\n* {task['id']}: {task['description']}"
            text_content += f"\n  Tools: {', '.join(task['tools'])}"

        text_content += """

---
Sloth Agent Framework
Reply with APPROVE or REJECT
"""

        msg.attach(MIMEText(text_content, "plain"))

        # HTML version
        html_content = f"""
<html><body>
<h2>Daily Plan Approval Required</h2>
<p><strong>Date:</strong> {request.summary}</p>
<p><strong>Request ID:</strong> {request.request_id}</p>

<h3>Tasks:</h3>
<ul>
"""
        for task in request.tasks:
            html_content += f"<li><strong>{task['id']}</strong>: {task['description']}<br/>Tools: {', '.join(task['tools'])}</li>"

        html_content += """
</ul>
<hr/>
<p><em>Sloth Agent Framework</em></p>
</body></html>
"""

        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(channel.smtp, channel.port) as server:
            server.starttls()
            server.send_message(msg)

        logger.info(f"Sent email approval request: {request.request_id}")

    def check_approval_status(self, request_id: str) -> str:
        """Check if a request has been approved."""
        # TODO: Implement status checking (file/db based for now)
        project_root = Path(__file__).parent.parent.parent.parent
        status_file = project_root / "approval_status" / f"{request_id}.json"

        if status_file.exists():
            return json.loads(status_file.read_text()).get("status", "pending")

        return "pending"
