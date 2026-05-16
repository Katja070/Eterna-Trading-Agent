# Eterna Trading Agent

A Python-based algorithmic trading agent that uses Claude (claude-opus-4-7) as its decision-making brain and executes trades on the Eterna perpetual futures exchange via its MCP Gateway.

## Architecture

```
agent.py          — Main async agent loop (Claude + agentic tool use)
tools.py          — Tool definitions + dispatcher (12 Eterna tools)
eterna_mcp.py     — Async MCP client (mcp package, streamable-http)
config.py         — Configuration from environment variables
strategies.py     — Pre-built strategy prompts
```

### How it works

1. `agent.py` sends a trading instruction to Claude (claude-opus-4-7 with adaptive thinking + streaming).
2. Claude calls tools directly: `get_balance`, `get_tickers`, `place_order`, etc.
3. `eterna_mcp.py` forwards each call to the Eterna MCP Gateway via the `mcp` Python package.
4. Results are returned to Claude, which continues reasoning until `end_turn`.

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Register your agent (first time only)

```bash
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env
# Leave ETERNA_API_KEY blank for now

python agent.py "Register a new trading agent called my-eterna-bot"
```

Save the API key printed in the output — it is shown only once.

### 3. Add your API key

Edit `.env` and set `ETERNA_API_KEY=eterna_mcp_...`

### 4. Deposit funds

```bash
python agent.py "Get my USDT deposit address on Arbitrum"
```

Send USDT to the address, then:

```bash
python agent.py "Transfer my deposited USDT to the trading wallet"
```

### 5. Run the agent

```bash
# Market scan (analysis only, no trades)
python agent.py "$(python -c "from strategies import get_strategy; print(get_strategy('market_scan'))")"

# Default: scan and trade if conditions are favorable
python agent.py

# Specific strategy
python agent.py "$(python -c "from strategies import get_strategy; print(get_strategy('momentum_scalping'))")"
```

## Available Strategies

| Strategy | Description |
|---|---|
| `momentum_scalping` | Scan for momentum, confirm with order book, trade with TP/SL |
| `market_scan` | Analysis only, no trades |
| `portfolio_review` | Review open positions and PnL |
| `close_all` | Close all positions and cancel all orders |
| `deposit` | Get deposit address and check deposit status |

## Tools Available to Claude

All 12 Eterna MCP Gateway tools:

| Tool | Description |
|---|---|
| `get_tickers` | Current price, 24h change, funding rate |
| `get_instruments` | Contract specs (lotSize, tickSize, leverage limits) |
| `get_orderbook` | Live order book (bid/ask levels) |
| `get_balance` | USDT equity and available margin |
| `get_positions` | Open perpetual futures positions |
| `get_orders` | Active and recent orders |
| `place_order` | Market or limit order with TP/SL/leverage |
| `close_position` | Close entire position at market |
| `get_deposit_address` | Deposit address for USDT/other coins |
| `get_deposit_records` | Deposit history and status |
| `transfer_to_trading` | Move funds from Funding to Trading wallet |
| `register_agent` | Create account and get API key (one-time) |

## Risk Warnings

- This agent trades real money on a live exchange.
- Always run `market_scan` first to verify connectivity.
- Review `.env` risk settings before running trading strategies.
- Default leverage is 5x — do not increase without understanding the risks.
- Minimum recommended balance: $20 USDT.
