"""
Async MCP client for the Eterna Trading Gateway.

Uses the official `mcp` Python package (streamable-http transport).
Authentication: Bearer token in Authorization header.
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


class EternaMCPClient:
    """
    Thin wrapper around an MCP ClientSession that calls Eterna tools directly.
    Use as an async context manager.
    """

    def __init__(self, url: str, api_key: str | None = None):
        self.url = url
        self.api_key = api_key
        self._session: ClientSession | None = None
        self._exit_stack = None

    async def __aenter__(self) -> "EternaMCPClient":
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        self._cm = streamablehttp_client(self.url, headers=headers)
        read, write, _ = await self._cm.__aenter__()
        self._session = ClientSession(read, write)
        await self._session.__aenter__()
        await self._session.initialize()
        return self

    async def __aexit__(self, *args):
        if self._session:
            await self._session.__aexit__(*args)
        await self._cm.__aexit__(*args)

    async def call(self, tool_name: str, args: dict | None = None) -> Any:
        """Call an Eterna tool and return the parsed result."""
        result = await self._session.call_tool(tool_name, args or {})
        # MCP returns content list; extract and parse the first text item
        for item in result.content:
            text = item.text if hasattr(item, "text") else str(item)
            try:
                return json.loads(text)
            except (json.JSONDecodeError, TypeError):
                return text
        return None

    # ------------------------------------------------------------------
    # Registration (unauthenticated)
    # ------------------------------------------------------------------

    async def register_agent(self, name: str) -> dict:
        return await self.call("register_agent", {"name": name})

    # ------------------------------------------------------------------
    # Market data
    # ------------------------------------------------------------------

    async def get_tickers(self, symbol: str | None = None) -> list[dict]:
        args = {}
        if symbol:
            args["symbol"] = symbol
        return await self.call("get_tickers", args)

    async def get_instruments(self, symbol: str | None = None) -> list[dict]:
        args = {}
        if symbol:
            args["symbol"] = symbol
        return await self.call("get_instruments", args)

    async def get_orderbook(self, symbol: str, limit: int = 25) -> dict:
        return await self.call("get_orderbook", {"symbol": symbol, "limit": limit})

    # ------------------------------------------------------------------
    # Account
    # ------------------------------------------------------------------

    async def get_balance(self) -> dict:
        return await self.call("get_balance", {})

    async def get_positions(self, symbol: str | None = None) -> list[dict]:
        args = {}
        if symbol:
            args["symbol"] = symbol
        return await self.call("get_positions", args)

    async def get_orders(self, symbol: str | None = None) -> list[dict]:
        args = {}
        if symbol:
            args["symbol"] = symbol
        return await self.call("get_orders", args)

    # ------------------------------------------------------------------
    # Trading
    # ------------------------------------------------------------------

    async def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        qty: str,
        price: str | None = None,
        leverage: str | None = None,
        take_profit: str | None = None,
        stop_loss: str | None = None,
        reduce_only: bool = False,
    ) -> dict:
        args: dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "orderType": order_type,
            "qty": qty,
            "reduceOnly": reduce_only,
        }
        if price:
            args["price"] = price
        if leverage:
            args["leverage"] = leverage
        if take_profit:
            args["takeProfit"] = take_profit
        if stop_loss:
            args["stopLoss"] = stop_loss
        return await self.call("place_order", args)

    async def close_position(self, symbol: str) -> dict:
        return await self.call("close_position", {"symbol": symbol})

    # ------------------------------------------------------------------
    # Funding
    # ------------------------------------------------------------------

    async def get_deposit_address(self, coin: str, chain_type: str) -> dict:
        return await self.call("get_deposit_address", {"coin": coin, "chainType": chain_type})

    async def get_deposit_records(self, coin: str | None = None) -> dict:
        args = {}
        if coin:
            args["coin"] = coin
        return await self.call("get_deposit_records", args)

    async def transfer_to_trading(self, coin: str, amount: str) -> dict:
        return await self.call("transfer_to_trading", {"coin": coin, "amount": amount})
