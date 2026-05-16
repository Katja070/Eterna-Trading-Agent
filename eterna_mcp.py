"""
MCP client for the Eterna Trading platform.
Implements the streamable-HTTP JSON-RPC 2.0 protocol.
"""

import json
import time
import httpx


class EternaMCPClient:
    def __init__(self, url: str, api_key: str | None = None):
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.session_id: str | None = None
        self._request_id = 0
        self._client = httpx.Client(timeout=120.0)

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _headers(self) -> dict:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        return headers

    def _send(self, payload: dict) -> dict:
        response = self._client.post(self.url, json=payload, headers=self._headers())
        response.raise_for_status()

        # Capture session ID from response headers
        if "mcp-session-id" in response.headers:
            self.session_id = response.headers["mcp-session-id"]

        content_type = response.headers.get("content-type", "")
        if "text/event-stream" in content_type:
            return self._parse_sse(response.text)
        return response.json()

    def _parse_sse(self, text: str) -> dict:
        """Parse SSE stream and return the last JSON-RPC result."""
        last_result = None
        for line in text.splitlines():
            if line.startswith("data:"):
                data = line[5:].strip()
                if data and data != "[DONE]":
                    try:
                        obj = json.loads(data)
                        if "result" in obj or "error" in obj:
                            last_result = obj
                    except json.JSONDecodeError:
                        pass
        if last_result is None:
            raise ValueError(f"No valid JSON-RPC result in SSE stream: {text[:500]}")
        return last_result

    def initialize(self):
        """Perform the MCP initialization handshake."""
        init_payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "eterna-trading-agent", "version": "1.0.0"},
            },
        }
        self._send(init_payload)

        # Send initialized notification (no response expected)
        notif_payload = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        }
        try:
            self._client.post(self.url, json=notif_payload, headers=self._headers())
        except Exception:
            pass  # Notifications may return 202 or empty body

    def execute_code(self, code: str) -> dict:
        """
        Run TypeScript code in the Eterna Deno sandbox.
        Returns the parsed result dict from the execution response.
        """
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {
                "name": "execute_code",
                "arguments": {"code": code},
            },
        }
        response = self._send(payload)

        if "error" in response:
            raise RuntimeError(f"MCP error: {response['error']}")

        # Unwrap: result.content[0].text -> JSON string -> {success, result, ...}
        content = response["result"]["content"]
        text = content[0]["text"]
        parsed = json.loads(text)

        if not parsed.get("success"):
            error_msg = parsed.get("error", "Unknown execution error")
            logs = parsed.get("logs", [])
            raise RuntimeError(f"Execution failed: {error_msg}\nLogs: {logs}")

        return parsed.get("result", {})

    def search_sdk(self, query: str) -> str:
        """Search the Eterna SDK documentation."""
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {
                "name": "search_sdk",
                "arguments": {"query": query},
            },
        }
        response = self._send(payload)

        if "error" in response:
            raise RuntimeError(f"MCP error: {response['error']}")

        content = response["result"]["content"]
        return content[0]["text"]

    def close(self):
        self._client.close()

    def __enter__(self):
        self.initialize()
        return self

    def __exit__(self, *_):
        self.close()
