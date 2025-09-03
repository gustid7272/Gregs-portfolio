import os, json, time, math
import requests

ALPACA_KEY = os.getenv("ALPACA_KEY_ID")
ALPACA_SECRET = os.getenv("ALPACA_SECRET_KEY")
ALPACA_BASE = os.getenv("ALPACA_PAPER_BASE_URL", "https://paper-api.alpaca.markets")

HEADERS = {
    "APCA-API-KEY-ID": ALPACA_KEY,
    "APCA-API-SECRET-KEY": ALPACA_SECRET
}

def get_account():
    return requests.get(f"{ALPACA_BASE}/v2/account", headers=HEADERS, timeout=10).json()

def get_positions():
    r = requests.get(f"{ALPACA_BASE}/v2/positions", headers=HEADERS, timeout=10)
    if r.status_code == 200:
        return {p["symbol"]: p for p in r.json()}
    return {}

def cancel_open_orders():
    requests.delete(f"{ALPACA_BASE}/v2/orders", headers=HEADERS, timeout=10)

def place_order(symbol, notional, side, tif="day"):
    data = {
        "symbol": symbol,
        "notional": str(round(abs(notional), 2)),
        "side": side,
        "type": "market",
        "time_in_force": tif
    }
    r = requests.post(f"{ALPACA_BASE}/v2/orders", headers=HEADERS, json=data, timeout=10)
    if r.status_code >= 300:
        print("Order error:", r.status_code, r.text)
    else:
        j = r.json(); print("Order ok:", j.get("id"), symbol, side, notional)

def main():
    # Load signals.json from the repo workspace
    with open("data/signals.json","r") as f:
        signals = json.load(f)

    acct = get_account()
    if acct.get("trading_blocked"):
        print("Trading blocked:", acct.get("account_blocked"))
        return

    equity = float(acct["equity"])
    cash_target = max(0.0, min(100.0, signals.get("cash_target_pct", 0.0))) / 100.0
    target_equity = equity * (1.0 - cash_target)

    # Build capped target weights
    pos_cfg = signals.get("positions", [])
    weights = {}
    for p in pos_cfg:
        t = p["ticker"]
        tgt = p.get("target_weight_pct", 0.0) / 100.0
        cap = p.get("max_weight_pct", 1.0) / 100.0
        weights[t] = min(tgt, cap)

    total = sum(weights.values())
    scale = (target_equity / total) if total > 0 else 0.0

    # Current positions
    current = get_positions()
    current_value = {sym: float(d.get("market_value", 0)) for sym, d in current.items()}

    MIN_NOTIONAL = 5.00  # ignore tiny dust adjustments
    cancel_open_orders()

    # Liquidate names not in targets
    for sym in list(current.keys()):
        if sym not in weights:
            place_order(sym, current_value.get(sym, 0), "sell")

    # Rebalance to targets
    for sym, w in weights.items():
        desired = w * scale
        held = current_value.get(sym, 0.0)
        diff = desired - held
        if abs(diff) >= MIN_NOTIONAL:
            side = "buy" if diff > 0 else "sell"
            place_order(sym, diff, side)

    # (Optional) Slack notify
    hook = os.getenv("SLACK_WEBHOOK_URL")
    if hook:
        text = f"Alpaca exec done • equity=${equity:.2f} • targets={len(weights)}"
        try:
            requests.post(hook, json={"text": text}, timeout=10)
        except Exception as e:
            print("Slack post failed:", e)

if __name__ == "__main__":
    assert ALPACA_KEY and ALPACA_SECRET, "Missing Alpaca API keys"
    main()
