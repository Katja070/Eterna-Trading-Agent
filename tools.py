"""
Tool definitions for Claude + implementations that call the Eterna MCP server.

Each tool definition follows the Anthropic tool_use format.
Each implementation generates TypeScript and calls eterna_mcp.execute_code().
"""

from __future__ import annotations
from typing import Any
from eterna_mcp import EternaMCPClient

# ---------------------------------------------------------------------------
# Tool definitions (passed to Claude)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "name": "get_account_status",
        "description": (
            "Retrieve current account balance, open perpetual futures positions, "
            "and open orders. Call this before placing any trade."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "coin": {
                    "type": "string",
                    "description": "Coin to check balance for (default: USDT)",
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_market_data",
        "description": (
            "Get current market data: ticker (last price, 24h change, volume, "
            "funding rate) and order book depth for one or more symbols."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbols": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of symbols, e.g. ['BTCUSDT', 'ETHUSDT']",
                },
                "orderbook_depth": {
                    "type": "integer",
                    "description": "Number of order book levels to fetch (default: 5)",
                },
            },
            "required": ["symbols"],
        },
    },
    {
        "name": "get_indicators",
        "description": (
            "Fetch technical indicators for a symbol. Supported: rsi, macd, ema, "
            "sma, bollinger_bands, vwap. Returns computed values for the requested indicators."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Trading symbol, e.g. BTCUSDT"},
                "indicators": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["rsi", "macd", "ema", "sma", "bollinger_bands", "vwap"],
                    },
                    "description": "Indicators to compute",
                },
                "interval": {
                    "type": "string",
                    "description": "Candle interval: 1, 3, 5, 15, 30, 60, 120, 240, D, W (default: 60)",
                },
                "period": {
                    "type": "integer",
                    "description": "Lookback period for SMA/EMA/RSI (default: 14)",
                },
            },
            "required": ["symbol", "indicators"],
        },
    },
    {
        "name": "place_order",
        "description": (
            "Place a perpetual futures order (market or limit). "
            "Always set a stop-loss. Optionally set take-profit and leverage."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "e.g. BTCUSDT"},
                "side": {"type": "string", "enum": ["Buy", "Sell"]},
                "qty": {"type": "string", "description": "Order quantity (base asset)"},
                "order_type": {
                    "type": "string",
                    "enum": ["Market", "Limit"],
                    "description": "default: Market",
                },
                "price": {
                    "type": "string",
                    "description": "Limit price (required for Limit orders)",
                },
                "stop_loss": {
                    "type": "string",
                    "description": "Stop-loss price (strongly recommended)",
                },
                "take_profit": {"type": "string", "description": "Take-profit price"},
                "leverage": {
                    "type": "integer",
                    "description": "Leverage to set before the order (1-125)",
                },
                "reduce_only": {
                    "type": "boolean",
                    "description": "If true, order only reduces an existing position",
                },
            },
            "required": ["symbol", "side", "qty"],
        },
    },
    {
        "name": "close_position",
        "description": "Close an entire open position at market price.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Symbol whose position to close"}
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "cancel_orders",
        "description": "Cancel all open orders for a symbol, or a specific order by ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "order_id": {
                    "type": "string",
                    "description": "Specific order ID to cancel; omit to cancel all",
                },
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "set_risk_controls",
        "description": (
            "Update take-profit, stop-loss, or trailing-stop on an existing position. "
            "Also used to change leverage for a symbol."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "take_profit": {"type": "string"},
                "stop_loss": {"type": "string"},
                "trailing_stop": {
                    "type": "string",
                    "description": "Trailing stop distance in price units",
                },
                "leverage": {"type": "integer"},
            },
            "required": ["symbol"],
        },
    },
]

# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


def get_account_status(mcp: EternaMCPClient, coin: str = "USDT") -> dict:
    code = f"""
const balance = await eterna.getBalance({{ coin: "{coin}" }});
const positions = await eterna.getPositions({{}});
const orders = await eterna.getOpenOrders({{}});

return {{
  balance: balance,
  positions: positions?.list ?? [],
  open_orders: orders?.list ?? [],
}};
"""
    return mcp.execute_code(code)


def get_market_data(
    mcp: EternaMCPClient, symbols: list[str], orderbook_depth: int = 5
) -> dict:
    symbols_json = str(symbols).replace("'", '"')
    code = f"""
const symbols = {symbols_json};
const depth = {orderbook_depth};

const tickers = await eterna.getTickers({{ symbol: symbols.length === 1 ? symbols[0] : undefined }});
const tickerList = (tickers?.list ?? []).filter((t: any) => symbols.includes(t.symbol));

const books: Record<string, any> = {{}};
for (const sym of symbols) {{
  try {{
    books[sym] = await eterna.getOrderbook({{ symbol: sym, limit: depth }});
  }} catch (e) {{
    books[sym] = null;
  }}
}}

return {{ tickers: tickerList, orderbooks: books }};
"""
    return mcp.execute_code(code)


def get_indicators(
    mcp: EternaMCPClient,
    symbol: str,
    indicators: list[str],
    interval: str = "60",
    period: int = 14,
) -> dict:
    parts = []
    for ind in indicators:
        if ind == "rsi":
            parts.append(
                f'result["rsi"] = await eterna.getRsi({{ symbol: "{symbol}", interval: "{interval}", period: {period} }});'
            )
        elif ind == "macd":
            parts.append(
                f'result["macd"] = await eterna.getMacd({{ symbol: "{symbol}", interval: "{interval}" }});'
            )
        elif ind == "ema":
            parts.append(
                f'result["ema"] = await eterna.getEma({{ symbol: "{symbol}", interval: "{interval}", period: {period} }});'
            )
        elif ind == "sma":
            parts.append(
                f'result["sma"] = await eterna.getSma({{ symbol: "{symbol}", interval: "{interval}", period: {period} }});'
            )
        elif ind == "bollinger_bands":
            parts.append(
                f'result["bollinger_bands"] = await eterna.getBollingerBands({{ symbol: "{symbol}", interval: "{interval}", period: {period} }});'
            )
        elif ind == "vwap":
            parts.append(
                f'result["vwap"] = await eterna.getVwap({{ symbol: "{symbol}", interval: "{interval}" }});'
            )

    indicator_code = "\n  ".join(parts)
    code = f"""
const result: Record<string, any> = {{}};
{indicator_code}
return result;
"""
    return mcp.execute_code(code)


def place_order(
    mcp: EternaMCPClient,
    symbol: str,
    side: str,
    qty: str,
    order_type: str = "Market",
    price: str | None = None,
    stop_loss: str | None = None,
    take_profit: str | None = None,
    leverage: int | None = None,
    reduce_only: bool = False,
) -> dict:
    steps = []

    if leverage is not None:
        steps.append(
            f'await eterna.setLeverage({{ symbol: "{symbol}", buyLeverage: "{leverage}", sellLeverage: "{leverage}" }});'
        )

    order_params: dict[str, Any] = {
        "symbol": symbol,
        "side": side,
        "orderType": order_type,
        "qty": qty,
        "reduceOnly": reduce_only,
    }
    if price:
        order_params["price"] = price
    if stop_loss:
        order_params["stopLoss"] = stop_loss
    if take_profit:
        order_params["takeProfit"] = take_profit

    params_json = json_encode(order_params)
    steps.append(f"const order = await eterna.placeOrder({params_json});")
    steps.append("return { order };")

    code = "\n".join(steps)
    return mcp.execute_code(code)


def close_position(mcp: EternaMCPClient, symbol: str) -> dict:
    code = f"""
const result = await eterna.closePosition({{ symbol: "{symbol}" }});
return {{ result }};
"""
    return mcp.execute_code(code)


def cancel_orders(
    mcp: EternaMCPClient, symbol: str, order_id: str | None = None
) -> dict:
    if order_id:
        code = f"""
const result = await eterna.cancelOrder({{ symbol: "{symbol}", orderId: "{order_id}" }});
return {{ result }};
"""
    else:
        code = f"""
const orders = await eterna.getOpenOrders({{ symbol: "{symbol}" }});
const list = orders?.list ?? [];
const results = [];
for (const o of list) {{
  try {{
    const r = await eterna.cancelOrder({{ symbol: "{symbol}", orderId: o.orderId }});
    results.push(r);
  }} catch (e) {{
    results.push({{ error: String(e) }});
  }}
}}
return {{ cancelled: results.length, results }};
"""
    return mcp.execute_code(code)


def set_risk_controls(
    mcp: EternaMCPClient,
    symbol: str,
    take_profit: str | None = None,
    stop_loss: str | None = None,
    trailing_stop: str | None = None,
    leverage: int | None = None,
) -> dict:
    steps = []

    if leverage is not None:
        steps.append(
            f'await eterna.setLeverage({{ symbol: "{symbol}", buyLeverage: "{leverage}", sellLeverage: "{leverage}" }});'
        )

    ts_params: dict[str, Any] = {"symbol": symbol}
    if take_profit:
        ts_params["takeProfit"] = take_profit
    if stop_loss:
        ts_params["stopLoss"] = stop_loss
    if trailing_stop:
        ts_params["trailingStop"] = trailing_stop

    if len(ts_params) > 1:  # has more than just symbol
        params_json = json_encode(ts_params)
        steps.append(f"const result = await eterna.setTradingStop({params_json});")
        steps.append("return { result };")
    else:
        steps.append("return { message: 'No risk params to update' };")

    code = "\n".join(steps)
    return mcp.execute_code(code)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def json_encode(obj: Any) -> str:
    """Encode a Python dict as a JS object literal string."""
    import json
    return json.dumps(obj)


# ---------------------------------------------------------------------------
# Dispatcher: maps tool name -> implementation
# ---------------------------------------------------------------------------

def dispatch_tool(mcp: EternaMCPClient, tool_name: str, tool_input: dict) -> Any:
    if tool_name == "get_account_status":
        return get_account_status(mcp, coin=tool_input.get("coin", "USDT"))
    elif tool_name == "get_market_data":
        return get_market_data(
            mcp,
            symbols=tool_input["symbols"],
            orderbook_depth=tool_input.get("orderbook_depth", 5),
        )
    elif tool_name == "get_indicators":
        return get_indicators(
            mcp,
            symbol=tool_input["symbol"],
            indicators=tool_input["indicators"],
            interval=tool_input.get("interval", "60"),
            period=tool_input.get("period", 14),
        )
    elif tool_name == "place_order":
        return place_order(
            mcp,
            symbol=tool_input["symbol"],
            side=tool_input["side"],
            qty=tool_input["qty"],
            order_type=tool_input.get("order_type", "Market"),
            price=tool_input.get("price"),
            stop_loss=tool_input.get("stop_loss"),
            take_profit=tool_input.get("take_profit"),
            leverage=tool_input.get("leverage"),
            reduce_only=tool_input.get("reduce_only", False),
        )
    elif tool_name == "close_position":
        return close_position(mcp, symbol=tool_input["symbol"])
    elif tool_name == "cancel_orders":
        return cancel_orders(
            mcp,
            symbol=tool_input["symbol"],
            order_id=tool_input.get("order_id"),
        )
    elif tool_name == "set_risk_controls":
        return set_risk_controls(
            mcp,
            symbol=tool_input["symbol"],
            take_profit=tool_input.get("take_profit"),
            stop_loss=tool_input.get("stop_loss"),
            trailing_stop=tool_input.get("trailing_stop"),
            leverage=tool_input.get("leverage"),
        )
    else:
        raise ValueError(f"Unknown tool: {tool_name}")
