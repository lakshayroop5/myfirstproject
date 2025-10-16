"""
Utility tools for common operations.

This module provides utility tools for file operations, email sending,
Slack notifications, and other common tasks.
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import logging

from .base import Tool, ToolResult, ToolStatus, ToolError

logger = logging.getLogger(__name__)


class FileTool(Tool):
    """Tool for file system operations."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.base_path = Path(config.get('base_path', '.'))
        self.allowed_extensions = config.get('allowed_extensions', [])
        self.max_file_size = config.get('max_file_size', 10 * 1024 * 1024)  # 10MB
        
    def validate_config(self) -> bool:
        """Validate file tool configuration."""
        if not self.base_path.exists():
            logger.warning(f"Base path does not exist: {self.base_path}")
        return True
    
    def _validate_path(self, file_path: str) -> Path:
        """Validate and resolve file path."""
        path = Path(file_path)
        
        # Resolve relative to base path
        if not path.is_absolute():
            path = self.base_path / path
        
        # Security check: ensure path is within base_path
        try:
            path.resolve().relative_to(self.base_path.resolve())
        except ValueError:
            raise ToolError(f"Path outside allowed directory: {file_path}", self.name)
        
        return path
    
    async def execute(self, operation: str, file_path: str,
                     content: str = None, encoding: str = 'utf-8',
                     **kwargs) -> ToolResult:
        """
        Execute file operation.
        
        Args:
            operation: Operation type ('read', 'write', 'append', 'delete', 'exists', 'list')
            file_path: Path to the file
            content: Content for write/append operations
            encoding: File encoding
            **kwargs: Additional parameters
            
        Returns:
            ToolResult with operation result
        """
        try:
            path = self._validate_path(file_path)
            
            if operation == "read":
                if not path.exists():
                    raise ToolError(f"File not found: {file_path}", self.name)
                
                content = path.read_text(encoding=encoding)
                data = {
                    "content": content,
                    "size": len(content),
                    "path": str(path)
                }
                
            elif operation == "write":
                if content is None:
                    raise ToolError("Content required for write operation", self.name)
                
                # Check file size
                if len(content.encode(encoding)) > self.max_file_size:
                    raise ToolError(f"File size exceeds limit: {self.max_file_size}", self.name)
                
                # Create parent directories
                path.parent.mkdir(parents=True, exist_ok=True)
                
                path.write_text(content, encoding=encoding)
                data = {
                    "bytes_written": len(content.encode(encoding)),
                    "path": str(path)
                }
                
            elif operation == "append":
                if content is None:
                    raise ToolError("Content required for append operation", self.name)
                
                # Create file if it doesn't exist
                if not path.exists():
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.touch()
                
                with open(path, 'a', encoding=encoding) as f:
                    f.write(content)
                
                data = {
                    "bytes_appended": len(content.encode(encoding)),
                    "path": str(path)
                }
                
            elif operation == "delete":
                if not path.exists():
                    raise ToolError(f"File not found: {file_path}", self.name)
                
                path.unlink()
                data = {"deleted": str(path)}
                
            elif operation == "exists":
                data = {
                    "exists": path.exists(),
                    "path": str(path)
                }
                
            elif operation == "list":
                if not path.exists():
                    raise ToolError(f"Directory not found: {file_path}", self.name)
                
                if not path.is_dir():
                    raise ToolError(f"Path is not a directory: {file_path}", self.name)
                
                files = []
                for item in path.iterdir():
                    files.append({
                        "name": item.name,
                        "path": str(item),
                        "is_file": item.is_file(),
                        "is_dir": item.is_dir(),
                        "size": item.stat().st_size if item.is_file() else None
                    })
                
                data = {
                    "files": files,
                    "count": len(files),
                    "path": str(path)
                }
                
            else:
                raise ToolError(f"Unknown operation: {operation}", self.name)
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                data=data
            )
            
        except Exception as e:
            logger.error(f"File operation error: {e}")
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.ERROR,
                error=ToolError(f"File operation error: {e}", self.name, e)
            )
    
    def get_schema(self) -> Dict[str, Any]:
        """Get file tool schema."""
        return {
            "name": self.name,
            "description": "File system operations tool",
            "parameters": {
                "operation": {
                    "type": "string",
                    "description": "File operation type",
                    "required": True,
                    "enum": ["read", "write", "append", "delete", "exists", "list"]
                },
                "file_path": {
                    "type": "string",
                    "description": "Path to the file or directory",
                    "required": True
                },
                "content": {
                    "type": "string",
                    "description": "Content for write/append operations",
                    "required": False
                },
                "encoding": {
                    "type": "string",
                    "description": "File encoding",
                    "default": "utf-8"
                }
            },
            "required": ["operation", "file_path"],
            "examples": [
                {
                    "operation": "read",
                    "file_path": "data/example.txt"
                },
                {
                    "operation": "write",
                    "file_path": "output/result.txt",
                    "content": "Hello, World!"
                }
            ]
        }


class EmailTool(Tool):
    """Tool for sending emails."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.smtp_server = config.get('smtp_server')
        self.smtp_port = config.get('smtp_port', 587)
        self.username = config.get('username')
        self.password = config.get('password')
        self.use_tls = config.get('use_tls', True)
        self.from_email = config.get('from_email')
        
    def validate_config(self) -> bool:
        """Validate email configuration."""
        required = [self.smtp_server, self.username, self.password, self.from_email]
        if not all(required):
            logger.error(f"Missing required email configuration for {self.name}")
            return False
        return True
    
    async def execute(self, to_email: Union[str, List[str]], subject: str,
                     body: str, html_body: str = None,
                     cc: Union[str, List[str]] = None,
                     bcc: Union[str, List[str]] = None,
                     **kwargs) -> ToolResult:
        """
        Send email.
        
        Args:
            to_email: Recipient email(s)
            subject: Email subject
            body: Plain text body
            html_body: HTML body (optional)
            cc: CC recipients (optional)
            bcc: BCC recipients (optional)
            **kwargs: Additional parameters
            
        Returns:
            ToolResult with send status
        """
        try:
            # Import email libraries
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            from email.mime.base import MIMEBase
            from email import encoders
            
            # Prepare message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.from_email
            msg['Subject'] = subject
            
            # Handle recipients
            if isinstance(to_email, str):
                to_email = [to_email]
            msg['To'] = ', '.join(to_email)
            
            if cc:
                if isinstance(cc, str):
                    cc = [cc]
                msg['Cc'] = ', '.join(cc)
            
            # Add body
            msg.attach(MIMEText(body, 'plain'))
            
            if html_body:
                msg.attach(MIMEText(html_body, 'html'))
            
            # Prepare recipient list
            recipients = to_email[:]
            if cc:
                recipients.extend(cc)
            if bcc:
                if isinstance(bcc, str):
                    bcc = [bcc]
                recipients.extend(bcc)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg, to_addrs=recipients)
            
            data = {
                "sent": True,
                "recipients": len(recipients),
                "to": to_email,
                "subject": subject
            }
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                data=data
            )
            
        except Exception as e:
            logger.error(f"Email send error: {e}")
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.ERROR,
                error=ToolError(f"Email send error: {e}", self.name, e)
            )
    
    def get_schema(self) -> Dict[str, Any]:
        """Get email tool schema."""
        return {
            "name": self.name,
            "description": "Email sending tool",
            "parameters": {
                "to_email": {
                    "type": ["string", "array"],
                    "description": "Recipient email address(es)",
                    "required": True
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject",
                    "required": True
                },
                "body": {
                    "type": "string",
                    "description": "Plain text email body",
                    "required": True
                },
                "html_body": {
                    "type": "string",
                    "description": "HTML email body",
                    "required": False
                },
                "cc": {
                    "type": ["string", "array"],
                    "description": "CC recipients",
                    "required": False
                },
                "bcc": {
                    "type": ["string", "array"],
                    "description": "BCC recipients",
                    "required": False
                }
            },
            "required": ["to_email", "subject", "body"],
            "examples": [
                {
                    "to_email": "user@example.com",
                    "subject": "Test Email",
                    "body": "This is a test email."
                }
            ]
        }


class SlackTool(Tool):
    """Tool for Slack notifications."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.webhook_url = config.get('webhook_url')
        self.bot_token = config.get('bot_token')
        self.default_channel = config.get('default_channel')
        
    def validate_config(self) -> bool:
        """Validate Slack configuration."""
        if not (self.webhook_url or self.bot_token):
            logger.error(f"Either webhook_url or bot_token required for {self.name}")
            return False
        return True
    
    async def execute(self, message: str, channel: str = None,
                     username: str = None, icon_emoji: str = None,
                     attachments: List[Dict] = None, **kwargs) -> ToolResult:
        """
        Send Slack message.
        
        Args:
            message: Message text
            channel: Slack channel (optional if using webhook)
            username: Bot username (optional)
            icon_emoji: Bot icon emoji (optional)
            attachments: Message attachments (optional)
            **kwargs: Additional parameters
            
        Returns:
            ToolResult with send status
        """
        try:
            # Import HTTP client
            import aiohttp
            
            if self.webhook_url:
                # Use webhook
                payload = {
                    "text": message,
                    "username": username,
                    "icon_emoji": icon_emoji,
                    "attachments": attachments
                }
                
                # Remove None values
                payload = {k: v for k, v in payload.items() if v is not None}
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(self.webhook_url, json=payload) as response:
                        if response.status == 200:
                            data = {"sent": True, "method": "webhook"}
                        else:
                            raise ToolError(f"Slack webhook error: {response.status}", self.name)
            
            elif self.bot_token:
                # Use Bot API
                url = "https://slack.com/api/chat.postMessage"
                headers = {"Authorization": f"Bearer {self.bot_token}"}
                
                payload = {
                    "channel": channel or self.default_channel,
                    "text": message,
                    "username": username,
                    "icon_emoji": icon_emoji,
                    "attachments": json.dumps(attachments) if attachments else None
                }
                
                # Remove None values
                payload = {k: v for k, v in payload.items() if v is not None}
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, headers=headers, data=payload) as response:
                        result = await response.json()
                        
                        if result.get("ok"):
                            data = {"sent": True, "method": "bot_api", "ts": result.get("ts")}
                        else:
                            raise ToolError(f"Slack API error: {result.get('error')}", self.name)
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                data=data
            )
            
        except Exception as e:
            logger.error(f"Slack send error: {e}")
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.ERROR,
                error=ToolError(f"Slack send error: {e}", self.name, e)
            )
    
    def get_schema(self) -> Dict[str, Any]:
        """Get Slack tool schema."""
        return {
            "name": self.name,
            "description": "Slack messaging tool",
            "parameters": {
                "message": {
                    "type": "string",
                    "description": "Message text to send",
                    "required": True
                },
                "channel": {
                    "type": "string",
                    "description": "Slack channel (required for bot API)",
                    "required": False
                },
                "username": {
                    "type": "string",
                    "description": "Bot username",
                    "required": False
                },
                "icon_emoji": {
                    "type": "string",
                    "description": "Bot icon emoji",
                    "required": False
                },
                "attachments": {
                    "type": "array",
                    "description": "Message attachments",
                    "required": False
                }
            },
            "required": ["message"],
            "examples": [
                {
                    "message": "Hello from the agent!",
                    "channel": "#general",
                    "icon_emoji": ":robot_face:"
                }
            ]
        }