"""
Tool definitions for Claude + async implementations that call the Eterna MCP Gateway.

All 12 Eterna tools are exposed to Claude, mapped 1-to-1.
"""

from __future__ import annotations

from typing import Any
from eterna_mcp import EternaMCPClient

# ---------------------------------------------------------------------------
# Tool definitions (passed to Claude via Anthropic API)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "name": "get_tickers",
        "description": (
            "Get current price, 24h change, volume, and funding rate for perpetual "
            "futures. Omit symbol to get all tickers. Use this to scan for momentum."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "e.g. 'BTCUSDT'. Omit to get all tickers.",
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_instruments",
        "description": (
            "Get contract specs (tick size, lot size, leverage limits, min/max qty). "
            "Call before placing an order to get lotSize for correct quantity rounding."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "e.g. 'BTCUSDT'. Omit to get all instruments.",
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_orderbook",
        "description": (
            "Get live order book for a symbol. Use to confirm trade direction: "
            "bid volume > ask volume = buyers dominating (bullish)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "e.g. 'BTCUSDT'"},
                "limit": {
                    "type": "integer",
                    "description": "Levels per side, 1-200, default 25",
                },
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "get_balance",
        "description": (
            "Get USDT balance, equity, and available margin for the trading account. "
            "Call this first to know available capital before sizing positions."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_positions",
        "description": "Get all open perpetual futures positions, or filter by symbol.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Omit for all positions"}
            },
            "required": [],
        },
    },
    {
        "name": "get_orders",
        "description": "Get active and recent orders. Omit symbol to get all orders.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Omit for all orders"}
            },
            "required": [],
        },
    },
    {
        "name": "place_order",
        "description": (
            "Place a market or limit perpetual futures order. "
            "Always set stopLoss for risk management. "
            "Position size formula: qty = (equity/4) / lastPrice, rounded to lotSize."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "e.g. 'BTCUSDT'"},
                "side": {"type": "string", "enum": ["Buy", "Sell"]},
                "orderType": {"type": "string", "enum": ["Market", "Limit"]},
                "qty": {"type": "string", "description": "Base asset quantity, e.g. '0.001'"},
                "price": {
                    "type": "string",
                    "description": "Limit price (required for Limit orders)",
                },
                "leverage": {
                    "type": "string",
                    "description": "Leverage multiplier as string, e.g. '5'. Max 5x recommended.",
                },
                "takeProfit": {"type": "string", "description": "Take-profit price"},
                "stopLoss": {"type": "string", "description": "Stop-loss price (strongly recommended)"},
                "reduceOnly": {
                    "type": "boolean",
                    "description": "If true, only reduces an existing position",
                },
            },
            "required": ["symbol", "side", "orderType", "qty"],
        },
    },
    {
        "name": "close_position",
        "description": "Close an entire open position at market price.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Symbol of the position to close"}
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "get_deposit_address",
        "description": (
            "Get a deposit address for a specific coin and blockchain. "
            "Use ARBI (Arbitrum) for USDT — lowest fees and fastest confirmation."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "coin": {"type": "string", "description": "e.g. 'USDT'"},
                "chainType": {
                    "type": "string",
                    "description": "e.g. 'ARBI', 'ETH', 'SOL'",
                },
            },
            "required": ["coin", "chainType"],
        },
    },
    {
        "name": "get_deposit_records",
        "description": "Get deposit history. Use to monitor pending deposits.",
        "input_schema": {
            "type": "object",
            "properties": {
                "coin": {
                    "type": "string",
                    "description": "Filter by coin, e.g. 'USDT'. Omit for all.",
                }
            },
            "required": [],
        },
    },
    {
        "name": "transfer_to_trading",
        "description": (
            "Move funds from the Funding wallet to the Trading wallet. "
            "Deposits arrive in the Funding wallet and must be transferred before trading."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "coin": {"type": "string", "description": "e.g. 'USDT'"},
                "amount": {"type": "string", "description": "Amount to transfer, e.g. '500.00'"},
            },
            "required": ["coin", "amount"],
        },
    },
    {
        "name": "register_agent",
        "description": (
            "Create a new agent account and receive an API key. "
            "Only needed once. The key is shown only once — save it immediately."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Display name for the agent"}
            },
            "required": ["name"],
        },
    },
]

# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

async def dispatch_tool(mcp: EternaMCPClient, tool_name: str, tool_input: dict) -> Any:
    if tool_name == "get_tickers":
        return await mcp.get_tickers(symbol=tool_input.get("symbol"))

    elif tool_name == "get_instruments":
        return await mcp.get_instruments(symbol=tool_input.get("symbol"))

    elif tool_name == "get_orderbook":
        return await mcp.get_orderbook(
            symbol=tool_input["symbol"],
            limit=tool_input.get("limit", 25),
        )

    elif tool_name == "get_balance":
        return await mcp.get_balance()

    elif tool_name == "get_positions":
        return await mcp.get_positions(symbol=tool_input.get("symbol"))

    elif tool_name == "get_orders":
        return await mcp.get_orders(symbol=tool_input.get("symbol"))

    elif tool_name == "place_order":
        return await mcp.place_order(
            symbol=tool_input["symbol"],
            side=tool_input["side"],
            order_type=tool_input["orderType"],
            qty=tool_input["qty"],
            price=tool_input.get("price"),
            leverage=tool_input.get("leverage"),
            take_profit=tool_input.get("takeProfit"),
            stop_loss=tool_input.get("stopLoss"),
            reduce_only=tool_input.get("reduceOnly", False),
        )

    elif tool_name == "close_position":
        return await mcp.close_position(symbol=tool_input["symbol"])

    elif tool_name == "get_deposit_address":
        return await mcp.get_deposit_address(
            coin=tool_input["coin"],
            chain_type=tool_input["chainType"],
        )

    elif tool_name == "get_deposit_records":
        return await mcp.get_deposit_records(coin=tool_input.get("coin"))

    elif tool_name == "transfer_to_trading":
        return await mcp.transfer_to_trading(
            coin=tool_input["coin"],
            amount=tool_input["amount"],
        )

    elif tool_name == "register_agent":
        return await mcp.register_agent(name=tool_input["name"])

    else:
        raise ValueError(f"Unknown tool: {tool_name}")
