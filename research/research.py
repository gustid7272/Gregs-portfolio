import os, json
from datetime import datetime, timezone

CASH_TARGET_PCT = 20.0
SAFE_STABLE = ["MSFT","AAPL","JNJ","PG","V","PEP","COST","WMT"]
RISKY = ["PLTR","TSLA"]
ANALYST = ["LMT","XOM","NEE","GOOGL"]

TARGETS = {
    **{t: 80.0/len(SAFE_STABLE) for t in SAFE_STABLE},
    **{t: 5.0/len(RISKY) for t in RISKY},
    **{t: 15.0/len(ANALYST) for t in ANALYST},
}

def build_signals():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    positions = []
    for tkr, w in TARGETS.items():
        segment = "safe" if tkr in SAFE_STABLE else ("risky" if tkr in RISKY else "analyst")
        max_cap = 6.0 if segment=="safe" else (1.0 if segment=="risky" else 5.0)
        positions.append({
            "ticker": tkr,
            "segment": segment,
            "target_weight_pct": round(w, 3),
            "max_weight_pct": max_cap,
            "stop_loss_pct": -15,
            "thesis_break_triggers": [
                "Earnings/guidance miss (8-K Item 2.02)",
                "Ratings downgrade to junk",
                "Regulatory denial of key product"
            ],
            "confidence": 3,
            "citations": []
        })
    return {
        "as_of": now,
        "rebalance_hint": "quarterly",
        "cash_target_pct": CASH_TARGET_PCT,
        "positions": positions,
        "notes": "Starter static allocation; replace with research engine."
    }

def main():
    os.makedirs("data", exist_ok=True)
    signals = build_signals()
    with open("data/signals.json","w") as f:
        json.dump(signals, f, indent=2)
    print("Wrote data/signals.json", signals["as_of"])

    hook = os.getenv("SLACK_WEBHOOK_URL")
    if hook:
        import requests
        requests.post(hook, json={"text": f"greg signals updated • {signals['as_of']} • {len(signals['positions'])} tickers"}, timeout=10)

if __name__ == "__main__":
    main()
