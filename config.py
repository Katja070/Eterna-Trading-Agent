"""
Configuration loaded from environment variables / .env file.
"""

import os
from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise EnvironmentError(f"Required environment variable '{name}' is not set.")
    return val


# Anthropic
ANTHROPIC_API_KEY: str = _require("ANTHROPIC_API_KEY")

# Eterna MCP
ETERNA_MCP_URL: str = os.getenv("ETERNA_MCP_URL", "https://mcp.eterna.exchange/mcp")
ETERNA_API_KEY: str | None = os.getenv("ETERNA_API_KEY")

# Strategy / risk
TRADING_OBJECTIVE: str = os.getenv(
    "TRADING_OBJECTIVE",
    "identify and execute profitable perpetual futures trades while rigorously managing risk",
)
MAX_RISK_PCT: float = float(os.getenv("MAX_RISK_PCT", "2.0"))
DEFAULT_LEVERAGE: int = int(os.getenv("DEFAULT_LEVERAGE", "5"))
MAX_LEVERAGE: int = int(os.getenv("MAX_LEVERAGE", "20"))
DEFAULT_SYMBOL: str = os.getenv("DEFAULT_SYMBOL", "BTCUSDT")

# Preferred trading symbols (comma-separated)
PREFERRED_SYMBOLS: list[str] = [
    s.strip()
    for s in os.getenv("PREFERRED_SYMBOLS", "BTCUSDT,ETHUSDT,SOLUSDT").split(",")
    if s.strip()
]

# Agent loop
MAX_TOOL_ROUNDS: int = int(os.getenv("MAX_TOOL_ROUNDS", "30"))
