"""
Eterna Trading Agent — main entry point.

Uses Claude (claude-opus-4-7) as the decision-making brain.
Trades via the Eterna MCP Gateway (12 direct trading tools).
"""

from __future__ import annotations

import asyncio
import json

import anthropic

import config
from eterna_mcp import EternaMCPClient
from tools import TOOL_DEFINITIONS, dispatch_tool

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are an expert algorithmic trading agent for cryptocurrency perpetual futures \
on the Eterna exchange (powered by Bybit infrastructure).

Your goal is to {objective}.

## Workflow

Before every trading session:
1. Call `get_balance` to check available capital.
2. Call `get_positions` to know current exposure.
3. Call `get_orders` to see any pending orders.

## Position Sizing

Use this formula:
  target_notional = totalEquity / 4       (allocate 25% of equity per position)
  qty = target_notional / lastPrice       (round DOWN to instrument lotSize)

Always call `get_instruments` for the symbol's `lotSize` before placing an order.
Maximum 4 open positions simultaneously. Maximum leverage: {max_leverage}x (default: {default_leverage}x).
Minimum account balance: $20 USDT — do not trade below this.

## Entry Signals (Momentum Scalping)

1. Scan `get_tickers`: positive `price24hPcnt` > +0.3% for long, < -0.3% for short.
2. Confirm with `get_orderbook`: bid_volume >= 1.1 × ask_volume (long), or ask >= 1.1 × bid (short).
3. Both signals must align. No signal = no trade.

## Exit Rules

- Take profit: 1.0% from entry price.
- Stop loss: 0.6% from entry price. **Always set `stopLoss` on every order.**
- Set `takeProfit` and `stopLoss` at order placement time. Let the exchange handle exits.

## Risk Rules

- Never risk more than {max_risk_pct}% of equity on a single trade.
- Do not open a second position on a symbol already held.
- If no balance is available for a new position, report the status and do not trade.

## Deposit Flow (if balance is zero)

1. Call `get_deposit_address` with coin `USDT`, chainType `ARBI`.
2. Report the address for the user to send USDT.
3. After funds arrive, call `get_deposit_records` to confirm.
4. Call `transfer_to_trading` to move funds to the trading wallet.

## Preferred Symbols

{preferred_symbols}

Always explain your reasoning before executing any trade. \
State the entry price, stop-loss, take-profit, and position size calculation.\
"""


def build_system_prompt() -> str:
    return SYSTEM_PROMPT.format(
        objective=config.TRADING_OBJECTIVE,
        max_risk_pct=config.MAX_RISK_PCT,
        default_leverage=config.DEFAULT_LEVERAGE,
        max_leverage=config.MAX_LEVERAGE,
        preferred_symbols=", ".join(config.PREFERRED_SYMBOLS),
    )


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

async def run_agent(user_message: str, verbose: bool = True) -> str:
    """
    Run a single agent session: send user_message, let Claude use tools
    until end_turn, and return the final text response.
    """
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    messages: list[dict] = [{"role": "user", "content": user_message}]
    system = build_system_prompt()

    async with EternaMCPClient(config.ETERNA_MCP_URL, config.ETERNA_API_KEY) as mcp:
        for round_num in range(config.MAX_TOOL_ROUNDS):
            if verbose:
                print(f"\n[Round {round_num + 1}] Calling Claude...", flush=True)

            with client.messages.stream(
                model="claude-opus-4-7",
                max_tokens=8096,
                thinking={"type": "adaptive"},
                system=[
                    {
                        "type": "text",
                        "text": system,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                tools=TOOL_DEFINITIONS,
                messages=messages,
            ) as stream:
                response = stream.get_final_message()

            if verbose:
                _print_response(response)

            messages.append({"role": "assistant", "content": response.content})
            stop_reason = response.stop_reason

            if stop_reason == "end_turn":
                return _extract_text(response)

            if stop_reason in ("tool_use", "pause_turn"):
                tool_results = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue

                    tool_name = block.name
                    tool_input = block.input

                    if verbose:
                        print(f"  -> {tool_name}({json.dumps(tool_input, indent=2)})", flush=True)

                    try:
                        result = await dispatch_tool(mcp, tool_name, tool_input)
                        content = json.dumps(result, default=str)
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": content,
                            }
                        )
                        if verbose:
                            print(f"  <- {content[:400]}", flush=True)
                    except Exception as exc:
                        error_msg = str(exc)
                        if verbose:
                            print(f"  <- ERROR: {error_msg}", flush=True)
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": json.dumps({"error": error_msg}),
                                "is_error": True,
                            }
                        )

                if tool_results:
                    messages.append({"role": "user", "content": tool_results})
                continue

            break  # Unexpected stop reason

    return _extract_text(response)


def _extract_text(response) -> str:
    return "\n".join(
        block.text for block in response.content if hasattr(block, "text")
    )


def _print_response(response) -> None:
    for block in response.content:
        if hasattr(block, "text"):
            print(f"\n[Claude]: {block.text}", flush=True)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Eterna Trading Agent")
    parser.add_argument(
        "instruction",
        nargs="?",
        default=(
            "Check account status (balance, positions, orders), then scan the preferred "
            "symbols for momentum trading opportunities. If a clear setup exists with "
            "confirming signals, execute a trade with proper stop-loss and take-profit."
        ),
        help="Trading instruction for the agent",
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress tool call output")
    args = parser.parse_args()

    print("=" * 60)
    print("Eterna Trading Agent")
    print("=" * 60)
    print(f"Instruction: {args.instruction}\n")

    result = asyncio.run(run_agent(args.instruction, verbose=not args.quiet))

    print("\n" + "=" * 60)
    print("Final response:")
    print("=" * 60)
    print(result)


if __name__ == "__main__":
    main()
