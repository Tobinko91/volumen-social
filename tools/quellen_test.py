"""Prueft alle Nachrichtenquellen. Aufruf:  python3 /opt/volumen-social/app/tools/quellen_test.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from social import news  # noqa: E402

meldungen, status = news.einsammeln(stunden=48)
for name, s in status.items():
    print(f"{'OK  ' if s.startswith('ok') else 'FEHLER'}  {name}: {s}")
print(f"\n{len(meldungen)} Meldungen der letzten 48 Stunden. Wichtigste Ereignisse:")
for g in news.buendeln(meldungen)[:5]:
    print(f"  {g['punkte']:>4}  {', '.join(g['quellen'])}: {g['meldungen'][0]['titel'][:80]}")
