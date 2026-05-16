# Eterna Trading Agent

A Python-based algorithmic trading agent that uses Claude (claude-opus-4-7) as its decision-making brain and executes trades on the Eterna perpetual futures exchange via an MCP server.

## Architecture

```
agent.py          — Main agent loop (Claude + agentic tool use)
tools.py          — Tool definitions + implementations (TypeScript -> execute_code)
eterna_mcp.py     — Streamable-HTTP MCP client (JSON-RPC 2.0 + SSE)
config.py         — Configuration from environment variables
strategies.py     — Pre-built strategy prompts
```

### How it works

1. `agent.py` sends a trading instruction to Claude (claude-opus-4-7 with adaptive thinking).
2. Claude decides which tools to call (get_account_status, get_market_data, get_indicators, place_order, etc.).
3. Each tool generates TypeScript code and calls `eterna_mcp.execute_code()`.
4. The Eterna MCP server runs the TypeScript in a Deno sandbox with the `eterna.*` SDK.
5. Results are returned to Claude, which continues reasoning until it reaches `end_turn`.

## Setup

```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY and ETERNA_API_KEY

pip install -r requirements.txt
```

## Usage

```bash
# Default: scan markets and trade if conditions are favorable
python agent.py

# Custom instruction
python agent.py "Close all open positions and cancel all pending orders"

# Pre-built strategy
python -c "
from agent import run_agent
from strategies import get_strategy
run_agent(get_strategy('market_scan'))
"

# Quiet mode (suppress tool call output)
python agent.py --quiet "What is my current account balance?"
```

## Available Strategies

| Strategy | Description |
|---|---|
| `momentum` | RSI + MACD momentum trades |
| `mean_reversion` | Bollinger Band + RSI mean reversion |
| `trend_following` | EMA-aligned trend following |
| `breakout` | Bollinger Band squeeze breakouts |
| `portfolio_review` | Review and manage open positions |
| `market_scan` | Analysis only, no trades |

## Tools Available to Claude

| Tool | Description |
|---|---|
| `get_account_status` | Balance, positions, open orders |
| `get_market_data` | Tickers, funding rate, order book |
| `get_indicators` | RSI, MACD, EMA, SMA, Bollinger Bands, VWAP |
| `place_order` | Market or limit order with TP/SL/leverage |
| `close_position` | Close entire position at market |
| `cancel_orders` | Cancel all or specific orders |
| `set_risk_controls` | Update TP/SL/trailing stop/leverage |

## Risk Warnings

- This agent trades real money on a live exchange.
- Always start with `market_scan` strategy to verify connectivity before trading.
- Review and understand the risk settings in `.env` before running trading strategies.
- Monitor the agent during initial runs.
