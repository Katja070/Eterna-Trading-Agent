"""
Pre-built strategy prompts for the trading agent.

Pass one of these as the instruction to agent.run_agent() to run a specific strategy.
"""

STRATEGIES = {
    "momentum": (
        "Scan BTCUSDT, ETHUSDT, and SOLUSDT for momentum trading opportunities. "
        "Look for symbols with RSI between 50-65 (bullish momentum) or 35-50 (bearish momentum), "
        "confirmed by MACD histogram direction. "
        "Check that price is trending above (long) or below (short) the 50-period EMA. "
        "If a clear setup exists with at least 2:1 reward/risk, enter a trade. "
        "Set stop-loss 1.5x ATR below entry for longs, above for shorts."
    ),

    "mean_reversion": (
        "Look for mean reversion setups on BTCUSDT, ETHUSDT, or SOLUSDT. "
        "Find symbols where price has touched or broken the lower Bollinger Band (oversold) "
        "or upper Bollinger Band (overbought). "
        "Confirm with RSI below 30 (oversold, go long) or above 70 (overbought, go short). "
        "Target the middle Bollinger Band as take-profit. "
        "Use conservative leverage (3x max) for mean reversion trades."
    ),

    "trend_following": (
        "Identify the strongest trending symbol among BTCUSDT, ETHUSDT, and SOLUSDT. "
        "A strong trend is defined as: price above/below 20 and 50 EMA, "
        "MACD signal line crossed bullish/bearish, and RSI between 45-65 (not overbought). "
        "Enter in the trend direction on a pullback to the 20 EMA. "
        "Trail stop-loss at the 20 EMA."
    ),

    "breakout": (
        "Scan BTCUSDT, ETHUSDT, and SOLUSDT for Bollinger Band squeeze breakouts. "
        "A squeeze occurs when the bands are narrow (low volatility). "
        "A breakout is when price closes above the upper band (bullish) or below the lower band (bearish) "
        "with increasing volume. Enter on breakout confirmation with a stop just inside the band. "
        "Target 2x the band width as take-profit."
    ),

    "portfolio_review": (
        "Review the current portfolio: check account balance, all open positions, and open orders. "
        "For each open position, evaluate whether the original thesis still holds based on current "
        "price action and indicators. "
        "Update or close positions that are no longer valid. "
        "Report a summary of the portfolio status and any actions taken."
    ),

    "market_scan": (
        "Perform a comprehensive market analysis. "
        "Check account status, then analyze BTCUSDT, ETHUSDT, SOLUSDT, and BNBUSDT. "
        "For each symbol, fetch RSI, MACD, and Bollinger Bands. "
        "Identify the top 1-2 highest-conviction setups. "
        "Provide a detailed market report but do NOT place any trades — analysis only."
    ),
}


def get_strategy(name: str) -> str:
    """Return the instruction string for a named strategy."""
    if name not in STRATEGIES:
        available = ", ".join(STRATEGIES.keys())
        raise ValueError(f"Unknown strategy '{name}'. Available: {available}")
    return STRATEGIES[name]


def list_strategies() -> list[str]:
    return list(STRATEGIES.keys())
