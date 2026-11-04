"""S30 Willkommensvideo (Wunsch Tobias 01./03.11.2026): 15-20 Sekunden mit Stimme, zum Anpinnen auf TikTok,
Instagram, X und als YouTube-Short. Laeuft einmal von selbst (tools/plan.sh), danach Merkdatei.
Keine Bot-Ergebnisse, keine Versprechen, nur was der Kanal taeglich bringt."""
from __future__ import annotations

ZEILEN = [
    "Who watches the crypto market while it sleeps? We do. This is WhaleSqueeze.",
    "Every day: which coins whales are buying or leaving, straight from on-chain data.",
    "Live alerts on hacks, ETF decisions and the Fed, in minutes, not hours.",
    "The market in 30 seconds, every day.",
    "And crypto explained, short and clear.",
    "No signals. No hype. Just data. Follow WhaleSqueeze.",
]
FAKTEN = {"sekunden": 30}


def szenen() -> dict:
    sz = [{"typ": "willkommen", "daten": {"schritt": i}, "vorlage": z} for i, z in enumerate(ZEILEN[:5])]
    sz.append({"typ": "outro", "daten": {}, "vorlage": ZEILEN[5]})
    return {"format": "willkommen", "sprache": "en", "szenen": sz, "fakten": FAKTEN, "titel": "Welcome to WhaleSqueeze"}


TELEGRAM = ("🐋 <b>Welcome to WhaleSqueeze</b>\n\nWe watch while the market sleeps.\n\n"
            "• <b>Whale of the day</b>: who is buying, who is leaving, straight from on-chain data\n"
            "• <b>Live crypto alerts</b>: hacks, ETF decisions, Fed moves, in minutes\n"
            "• <b>Market in 30 seconds</b>: the biggest moves, every day\n"
            "• <b>Crypto explained</b>: short and clear\n\n"
            "No signals. No hype. Just data.\n\n<i>Not financial advice.</i>")
X = ("Welcome to WhaleSqueeze 🐋\nWhale of the day · live crypto alerts · market in 30 seconds · crypto explained.\n"
     "No signals. No hype. Just data.\nNot financial advice.")
