"""
Pre-built strategy prompts for the trading agent.
"""

STRATEGIES = {
    "momentum_scalping": (
        "Run the momentum scalping strategy on the preferred symbols. "
        "Steps:\n"
        "1. Call get_balance and get_positions to assess current state.\n"
        "2. If fewer than 4 positions are open, scan get_tickers for symbols with "
        "|price24hPcnt| > 0.3%.\n"
        "3. For each candidate, call get_orderbook to confirm direction "
        "(bid_vol >= 1.1x ask_vol for long, ask_vol >= 1.1x bid_vol for short).\n"
        "4. Skip symbols already in positions.\n"
        "5. For confirmed setups: call get_instruments for lotSize, calculate qty "
        "(equity/4 / lastPrice, rounded to lotSize), then place_order with 5x leverage, "
        "stopLoss at 0.6% from entry, takeProfit at 1.0% from entry.\n"
        "6. Report all actions taken and any positions already open."
    ),

    "market_scan": (
        "Perform a market analysis — no trades. "
        "Call get_balance, get_positions, get_orders. "
        "Call get_tickers for BTCUSDT, ETHUSDT, SOLUSDT and check price24hPcnt, "
        "fundingRate, and volume24h. "
        "Call get_orderbook for each to assess bid/ask imbalance. "
        "Summarize the market state and identify 1-2 highest-conviction setups "
        "(but do NOT place any orders)."
    ),

    "portfolio_review": (
        "Review the current portfolio. "
        "Call get_balance, get_positions, get_orders. "
        "For each open position, report symbol, side, size, entry price, current mark price, "
        "unrealised PnL, and stop-loss/take-profit levels. "
        "Identify any positions missing stop-losses. "
        "Report total equity, margin utilisation, and overall PnL."
    ),

    "close_all": (
        "Close all open positions and cancel all open orders. "
        "First call get_positions to list all open positions. "
        "Then call close_position for each one. "
        "Then call get_orders and use close_position with reduceOnly=true for any remaining. "
        "Confirm the final state with get_balance and get_positions."
    ),

    "deposit": (
        "Help me deposit USDT to start trading. "
        "Call get_deposit_address with coin='USDT' and chainType='ARBI'. "
        "Report the deposit address clearly. "
        "Then call get_deposit_records to show any pending or recent deposits. "
        "Explain that deposits on Arbitrum typically confirm in 1-5 minutes."
    ),
}


def get_strategy(name: str) -> str:
    if name not in STRATEGIES:
        available = ", ".join(STRATEGIES.keys())
        raise ValueError(f"Unknown strategy '{name}'. Available: {available}")
    return STRATEGIES[name]


def list_strategies() -> list[str]:
    return list(STRATEGIES.keys())
