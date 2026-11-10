"""KI-Stimme je Szene. Anbieter (config stimme.anbieter):
- openai (seit 03.11.2026, Entscheidung Tobias): gpt-4o-mini-tts, Schluessel `openai_api_key`. Kosten ca. 1 $/Monat.
  OpenAI schaltet diesen Weg am 6.1.2027 ab -> rechtzeitig umstellen.
- google (seit 01.11.2026, Wunsch Tobias): Google Cloud Text-to-Speech, Stimme „Chirp 3 HD“.
  1 Mio Zeichen/Monat gratis, wir brauchen ca. 50.000. Schluessel `google_tts_key` in secrets.yaml.
- elevenlabs: frueherer Anbieter (Kosten), Schluessel `elevenlabs_api_key`.
Ohne Schluessel oder bei einem Fehler: Stille in passender Laenge, das Video entsteht trotzdem (ohne Stimme)."""
from __future__ import annotations

import base64
import subprocess
from pathlib import Path

import requests


def dauer(datei: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(datei)],
        capture_output=True, text=True, check=True,
    ).stdout
    return float(out.strip())


def _stille(datei: Path, sekunden: float) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
         "-t", f"{sekunden:.2f}", "-c:a", "aac", str(datei)],
        check=True,
    )


class StimmeFehlt(Exception):
    pass


def voice_id(cfg: dict, key: str) -> str:
    """Feste ID aus config.yaml oder Suche nach dem Namen der eigenen Stimme im ElevenLabs-Konto."""
    st = cfg["stimme"]
    if st.get("voice_id"):
        return st["voice_id"]
    name = (st.get("voice_name") or "").strip().lower()
    r = requests.get("https://api.elevenlabs.io/v1/voices", headers={"xi-api-key": key}, timeout=30)
    r.raise_for_status()
    for v in r.json().get("voices", []):
        if (v.get("name") or "").strip().lower() == name:
            st["voice_id"] = v["voice_id"]          # fuer diesen Lauf merken
            return v["voice_id"]
    raise StimmeFehlt(f"Stimme '{st.get('voice_name')}' nicht im ElevenLabs-Konto gefunden")


def woerter_aus_ausrichtung(al: dict) -> list[dict]:
    """ElevenLabs-Zeitmarken je Zeichen -> je Wort {w, a, e} in Sekunden (fuer animierte Untertitel)."""
    out, akt = [], None
    for c, a, e in zip(al.get("characters", []), al.get("character_start_times_seconds", []),
                       al.get("character_end_times_seconds", [])):
        if c.isspace():
            if akt:
                out.append(akt)
            akt = None
        elif akt is None:
            akt = {"w": c, "a": round(a, 3), "e": round(e, 3)}
        else:
            akt["w"] += c
            akt["e"] = round(e, 3)
    if akt:
        out.append(akt)
    return out


def _gerundet(v: float) -> tuple[str, bool]:
    """Zahl fuer die Stimme runden (Wunsch Tobias 05.11.2026: „19% statt 19.24%, dann approx“).
    ab 10: ganze Zahl · 1 bis 10: eine Stelle · unter 1: zwei gueltige Stellen. -> (Text, wurde gerundet)."""
    if v >= 10:
        r = f"{round(v):,}"
    elif v >= 1:
        r = f"{round(v, 1):g}"
    else:
        r = f"{float(f'{v:.2g}'):g}"
    return r, float(r.replace(",", "")) != v


def sprech_wort(w: str) -> list[str]:
    """Ein angezeigtes Wort -> gesprochene Woerter. Nur fuer den Ton; Untertitel zeigen die genaue Zahl.
    $12.95 -> about 13 dollars · 19.24% -> about 19% · +17.1% -> about +17% · -0.29% -> about -0.3%
    $10,000 -> 10,000 dollars · $0.04512 -> about 0.045 dollars · 6.0x -> 6 times (Fehler 04./05.11.2026: Brian
    nuschelte Preise und sprach Nachkommastellen zu schnell)."""
    import re
    # 06.11.2026 (ALLO-Reel): „~160M“, „~17×“ las Brian als Tilde/„M“/Zeichen, Tobias hoerte nicht, ob Millionen
    # oder Milliarden. ~/≈ -> about, K/M/B/T -> thousand/million/billion/trillion, × -> times.
    m = re.fullmatch(r"([(\[]?)[~≈]([^~≈].*)", w)
    if m:
        rest = sprech_wort(m.group(1) + m.group(2))
        return rest if rest[0] == "about" else ["about"] + rest
    w = w.replace("×", "x")
    m = re.fullmatch(r"([(\[]?)([+\-−]?)(\$?)(\d[\d,]*(?:\.\d+)?)([KkMBT]n?)([.,:;!?)\]]*)", w)
    if m:
        vor, vz, dollar, zahl, einheit, rest = m.groups()
        wort = {"K": "thousand", "k": "thousand", "M": "million", "B": "billion", "Bn": "billion",
                "T": "trillion", "Mn": "million"}.get(einheit)
        if wort:
            r, rund = _gerundet(float(zahl.replace(",", "")))
            minus = ["minus"] if vz in "-−" and vz else []
            schluss = [wort, "dollars" + rest] if dollar else [wort + rest]
            return (["about"] if rund else []) + minus + [vor + r] + schluss
    m = re.fullmatch(r"([(\[]?)\$(\d[\d,]*(?:\.\d+)?)([.,:;!?)\]]*)", w)
    if m:
        vor, zahl, rest = m.groups()
        r, rund = _gerundet(float(zahl.replace(",", "")))
        return (["about"] if rund else []) + [vor + r, "dollars" + rest]
    m = re.fullmatch(r"([(\[]?)([+\-−]?)(\d[\d,]*(?:\.\d+)?)%([.,:;!?)\]]*)", w)
    if m:
        vor, vz, zahl, rest = m.groups()
        r, rund = _gerundet(float(zahl.replace(",", "")))
        return (["about"] if rund else []) + [vor + vz.replace("−", "-") + r + "%" + rest]
    m = re.fullmatch(r"(\d+(?:\.\d+)?)x([.,:;!?]*)", w)
    if m:
        r, rund = _gerundet(float(m.group(1)))
        return (["about"] if rund else []) + [r, "times" + m.group(2)]
    return [w]


EINER = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
         "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
ZEHNER = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
MONATE = {"Jan": "January", "Feb": "February", "Mar": "March", "Apr": "April", "Jun": "June", "Jul": "July",
          "Aug": "August", "Sep": "September", "Sept": "September", "Oct": "October", "Nov": "November",
          "Dec": "December"}


def _unter_tausend(n: int) -> list[str]:
    out = []
    if n >= 100:
        out += [EINER[n // 100], "hundred"]
        n %= 100
    if n >= 20:
        out.append(ZEHNER[n // 10] + (f"-{EINER[n % 10]}" if n % 10 else ""))
    elif n or not out:
        out.append(EINER[n])
    return out


def zahl_worte(n: int) -> list[str]:
    """165000 -> one hundred sixty-five thousand (bis Billionen)."""
    if n == 0:
        return ["zero"]
    out = []
    for wert, name in ((10 ** 12, "trillion"), (10 ** 9, "billion"), (10 ** 6, "million"), (1000, "thousand")):
        if n >= wert:
            out += _unter_tausend(n // wert) + [name]
            n %= wert
    if n:
        out += _unter_tausend(n)
    return out


def jahr_worte(j: int) -> list[str]:
    """2021 -> twenty twenty-one · 2005 -> two thousand five · 1999 -> nineteen ninety-nine."""
    if 2000 <= j <= 2009:
        return zahl_worte(j)
    a, b = divmod(j, 100)
    return _unter_tausend(a) + (["hundred"] if b == 0 else (["oh", EINER[b]] if b < 10 else _unter_tausend(b)))


def worte(t: str) -> list[str]:
    """06.11.2026 (MEXC-Reel: „May 2021“ mit Haken, „$16B“ unklar): Das Flash-Modell von ElevenLabs normalisiert
    Zahlen nicht selbst (nur im Enterprise-Tarif). Darum schreiben wir jede Zahl als Woerter aus."""
    import re
    m = re.fullmatch(r"([(\[\"“]?)(.*?)([.,:;!?)\]\"”]*)", t)
    vor, kern, nach = m.groups()
    if kern in MONATE:
        return [vor + MONATE[kern] + nach]
    m = re.fullmatch(r"#(\d+)", kern)
    if m:
        return [vor + "number"] + zahl_worte(int(m.group(1)))[:-1] + [zahl_worte(int(m.group(1)))[-1] + nach]
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", kern)
    if m:
        h, mi = int(m.group(1)), int(m.group(2))
        z = zahl_worte(h) + (["hundred"] if mi == 0 and (h >= 13 or h == 0) else [] if mi == 0
                              else (["oh", EINER[mi]] if mi < 10 else _unter_tausend(mi)))
        z[0], z[-1] = vor + z[0], z[-1] + nach
        return z
    m = re.fullmatch(r"([+\-−]?)(\d[\d,]*)(?:\.(\d+))?(%?)", kern)
    if not m:
        return [t]
    vz, ganz, dez, pz = m.groups()
    n = int(ganz.replace(",", ""))
    if not dez and not pz and not vz and "," not in ganz and 1900 <= n <= 2099 and len(ganz) == 4:
        z = jahr_worte(n)
    else:
        z = (["minus"] if vz in ("-", "−") else ["plus"] if vz == "+" else []) + zahl_worte(n)
        if dez:
            z += ["point"] + [EINER[int(c)] for c in dez]
        if pz:
            z.append("percent")
    z[0], z[-1] = vor + z[0], z[-1] + nach
    return z


ORDINAL = {"one": "first", "two": "second", "three": "third", "five": "fifth", "eight": "eighth", "nine": "ninth",
           "twelve": "twelfth"}


def _ordinal(w: str) -> str:
    """nine -> ninth, twenty-one -> twenty-first, eleven -> eleventh, thirty -> thirtieth."""
    vorn, _, letzt = w.rpartition("-")
    if letzt in ORDINAL:
        o = ORDINAL[letzt]
    elif letzt.endswith("y"):
        o = letzt[:-1] + "ieth"
    else:
        o = letzt + "th"
    return f"{vorn}-{o}" if vorn else o


def sprechbar(text: str) -> tuple[str, list[int]]:
    """-> (Text fuer die Stimme, Anzahl gesprochener Woerter je angezeigtem Wort)."""
    import re
    gruppen, vorher = [], ""
    for w in text.split():
        g = [x for t in sprech_wort(w) for x in worte(t)]
        tag = re.fullmatch(r"(\d{1,2})([.,:;!?)]*)", w)
        if tag and vorher.strip("(") in MONATE.values() | MONATE.keys() and 1 <= int(tag.group(1)) <= 31:
            g[-1] = _ordinal(g[-1].rstrip(".,:;!?)")) + tag.group(2)   # Nov 11 -> November eleventh
        gruppen.append(g)
        vorher = w
    return " ".join(t for g in gruppen for t in g), [len(g) for g in gruppen]


def zurueck_auf_anzeige(text: str, gesprochen: list[dict], laengen: list[int]) -> list[dict]:
    """Zeitmarken der gesprochenen Woerter auf die angezeigten Woerter zurueckrechnen."""
    anzeige = text.split()
    if sum(laengen) != len(gesprochen) or len(anzeige) != len(laengen):
        return gesprochen
    out, i = [], 0
    for w, n in zip(anzeige, laengen):
        teil = gesprochen[i:i + n]
        out.append({"w": w, "a": teil[0]["a"], "e": teil[-1]["e"]})
        i += n
    return out


def _elevenlabs(text: str, datei: Path, cfg: dict, key: str) -> None:
    """Ton + Zeitmarken je Wort (Endpunkt with-timestamps, gleicher Preis); Marken als <datei>.json daneben."""
    vid = voice_id(cfg, key)
    anzeige = text
    text, laengen = sprechbar(text)
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{vid}/with-timestamps",
        headers={"xi-api-key": key, "content-type": "application/json"},
        json={"text": text, "model_id": cfg["stimme"]["modell"],
              "voice_settings": {"stability": 0.55, "similarity_boost": 0.75, "style": 0.15}},
        timeout=120,
    )
    if r.status_code >= 300:   # verstaendlicher Grund statt nur „401“ (z. B. Guthaben leer, Tarif ohne API)
        try:
            det = r.json().get("detail")
            msg = det.get("message") if isinstance(det, dict) else str(det)
        except Exception:
            msg = r.text[:200]
        raise StimmeFehlt(f"ElevenLabs: {r.status_code} {msg}")
    j = r.json()
    datei.write_bytes(base64.b64decode(j["audio_base64"]))
    woerter = zurueck_auf_anzeige(anzeige, woerter_aus_ausrichtung(j.get("alignment") or {}), laengen)
    if woerter:
        import json
        datei.with_suffix(".json").write_text(json.dumps(woerter))


def elevenlabs_guthaben(key: str, get=requests.get) -> dict:
    """Tarif und verbleibende Credits (fuer Hoerprobe und Gesundheits-Check)."""
    r = get("https://api.elevenlabs.io/v1/user/subscription", headers={"xi-api-key": key}, timeout=30)
    if r.status_code >= 300:
        raise StimmeFehlt(f"ElevenLabs-Konto: {r.status_code}")
    j = r.json()
    return {"tarif": j.get("tier"), "verbraucht": j.get("character_count"), "limit": j.get("character_limit")}


GOOGLE_TTS = "https://texttospeech.googleapis.com/v1/text:synthesize"


def _google(text: str, datei: Path, cfg: dict, key: str, post=requests.post) -> None:
    st = cfg["stimme"]
    name = st.get("google_stimme") or "en-US-Chirp3-HD-Charon"
    audio = {"audioEncoding": "MP3"}
    if st.get("tempo"):
        audio["speakingRate"] = st["tempo"]
    r = post(GOOGLE_TTS, params={"key": key}, timeout=60,
             json={"input": {"text": text}, "voice": {"languageCode": "-".join(name.split("-")[:2]), "name": name},
                   "audioConfig": audio})
    if r.status_code >= 300:
        try:
            msg = r.json().get("error", {}).get("message", "")
        except Exception:
            msg = r.text[:200]
        raise StimmeFehlt(f"Google-Stimme: {r.status_code} {msg}")
    datei.write_bytes(base64.b64decode(r.json()["audioContent"]))


OPENAI_TTS = "https://api.openai.com/v1/audio/speech"
OPENAI_STIL = ("Calm, confident narrator of a factual crypto data channel. Clear and natural, slightly energetic, "
               "short pauses between sentences. Read numbers and percent signs naturally.")


def _openai(text: str, datei: Path, cfg: dict, key: str, post=requests.post) -> None:
    """OpenAI-Stimme (Entscheidung Tobias 03.11.2026). Hinweis: OpenAI schaltet diesen einfachen Weg
    (gpt-4o-mini-tts, /v1/audio/speech) am 6.1.2027 ab -> bis dahin umstellen (siehe ideen-backlog S17)."""
    st = cfg["stimme"]
    body = {"model": st.get("openai_modell") or "gpt-4o-mini-tts", "voice": st.get("openai_stimme") or "cedar",
            "input": text, "response_format": "mp3"}
    if "mini-tts" in body["model"]:
        body["instructions"] = st.get("openai_stil") or OPENAI_STIL
    r = post(OPENAI_TTS, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
             json=body, timeout=90)
    if r.status_code >= 300:
        try:
            msg = r.json().get("error", {}).get("message", "")
        except Exception:
            msg = r.text[:200]
        raise StimmeFehlt(f"OpenAI-Stimme: {r.status_code} {msg}")
    datei.write_bytes(r.content)


SCHLUESSEL = {"google": "google_tts_key", "openai": "openai_api_key", "elevenlabs": "elevenlabs_api_key"}
ERZEUGER = {"google": "_google", "openai": "_openai", "elevenlabs": "_elevenlabs"}


def schluessel(cfg: dict, geheim: dict) -> str | None:
    """Passender Schluessel zum eingestellten Anbieter."""
    anbieter = (cfg.get("stimme") or {}).get("anbieter", "elevenlabs")
    return geheim.get(SCHLUESSEL.get(anbieter, "elevenlabs_api_key"))


def sprechen(zeilen: list[str], ordner: Path, cfg: dict, key: str | None) -> tuple[list[Path], list[float], str]:
    """Erzeugt je Zeile eine Tondatei. Gibt (Dateien, Dauern, Quelle) zurueck."""
    ordner.mkdir(parents=True, exist_ok=True)
    st = cfg["stimme"]
    anbieter = st.get("anbieter", "elevenlabs")
    echt = bool(key and st.get("aktiv", True) and (anbieter != "elevenlabs" or st.get("voice_id") or st.get("voice_name")))
    if echt:
        try:
            return _echt(zeilen, ordner, cfg, key, anbieter)
        except Exception as e:   # Stimme kaputt -> Video trotzdem bauen, Hinweis an Tobias ueber die Quelle
            print("Stimme fehlgeschlagen, Video ohne Stimme:", e)
            fehler = f"stille (Stimme fehlgeschlagen: {str(e)[:120]})"
            dateien, dauern, _ = sprechen(zeilen, ordner, dict(cfg, stimme=dict(st, aktiv=False)), None)
            return dateien, dauern, fehler
    dateien, dauern = [], []
    for i, z in enumerate(zeilen):
        f = ordner / f"ton_{i:02d}.m4a"
        d = max(cfg["video"]["min_szene_s"], len(z.split()) / cfg["video"]["woerter_pro_sekunde"] + 0.4)
        _stille(f, d)
        dateien.append(f)
        dauern.append(max(d, cfg["video"]["min_szene_s"]))
    return dateien, dauern, "stille"


def _echt(zeilen, ordner, cfg, key, anbieter):
    erzeuger = globals()[ERZEUGER.get(anbieter, "_elevenlabs")]
    dateien, dauern = [], []
    for i, z in enumerate(zeilen):
        f = ordner / f"ton_{i:02d}.mp3"
        erzeuger(z, f, cfg, key)
        d = dauer(f) + 0.35          # kurze Pause nach jedem Satz
        dateien.append(f)
        dauern.append(max(d, cfg["video"]["min_szene_s"]))
    return dateien, dauern, anbieter
