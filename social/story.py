"""Instagram-Story: jeden Instagram-Beitrag zusaetzlich als Story teilen (Wunsch Tobias 01.11.2026, Punkt C).

Stories sehen vor allem Leute, die schon folgen -> mehr Kontakte mit dem eigenen Publikum, ohne Mehrarbeit.
- Bild-Beitrag (4:5): wird in ein 9:16-Bild im Nachtleuchten-Design gesetzt (Marke oben, Beitrag mittig).
- Video (Reel, 9:16): dasselbe Video als Story.
Die Instagram-Schnittstelle erlaubt keine Sticker/Links in Stories; der Hinweis aufs Profil steht im Bild.
"""
from __future__ import annotations

import os
import secrets as _zufall
import time
from pathlib import Path

from PIL import Image, ImageDraw

from . import design, kanaele

W, H = 1080, 1920
TEXT = {"en": "NEW POST · TAP THE PROFILE", "de": "NEUER BEITRAG · PROFIL ANTIPPEN"}


def story_bild(bild: Path, ziel: Path, lang: str = "en") -> Path:
    """4:5-Beitrag -> 9:16-Story im Corporate Design."""
    th = design.thema_waehlen("markt", f"story:{bild.parent.name}")
    img = design.hintergrund(th, W, H, saat=7)
    design.marke(img, th, 90, 150, 70)
    post = Image.open(bild).convert("RGB")
    breite = 920
    post = post.resize((breite, int(post.height * breite / post.width)))
    y = 330
    rahmen = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(rahmen).rounded_rectangle([(W - breite) // 2 - 6, y - 6, (W + breite) // 2 + 6, y + post.height + 6],
                                             radius=34, fill=design.rgb(th.akzent, 90))
    img.alpha_composite(rahmen)
    maske = Image.new("L", post.size, 0)
    ImageDraw.Draw(maske).rounded_rectangle([0, 0, post.width, post.height], radius=28, fill=255)
    img.paste(post, ((W - breite) // 2, y), maske)
    d = ImageDraw.Draw(img)
    t = TEXT.get(lang, TEXT["en"])
    f = design.font("Bold", 40)
    d.text(((W - d.textlength(t, font=f)) / 2, y + post.height + 70), t, font=f, fill=th.akzent)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(ziel, "JPEG", quality=92)
    return ziel


def posten(geheim: dict, medium: Path, warten=time.sleep, pruefen_url=None, lang: str | None = None) -> str:
    """Story veroeffentlichen. medium = post.png oder video.mp4 des Vorschlags."""
    if not kanaele.verfuegbar(geheim)["instagram"]:
        raise kanaele.NichtEingerichtet("Instagram-Token fehlt (schluessel.py, Punkt 9)")
    token = geheim["instagram_token"]
    kanaele.IG_ORDNER.mkdir(parents=True, exist_ok=True)
    video = medium.suffix == ".mp4"
    datei = kanaele.IG_ORDNER / (_zufall.token_hex(16) + (".mp4" if video else ".jpg"))
    if video:
        datei.write_bytes(medium.read_bytes())
    else:
        story_bild(medium, datei, lang or design.SPRACHE)
    os.chmod(datei, 0o644)
    url = kanaele.IG_URL + datei.name
    try:
        r = (pruefen_url or (lambda u: __import__("requests").head(u, timeout=20).status_code))(url)
        if r != 200:
            raise kanaele.NichtEingerichtet(f"Medien-Ordner nicht erreichbar ({r})")
        uid = geheim.get("instagram_user_id") or kanaele._ig("GET", "me", token, fields="user_id")["user_id"]
        c = kanaele._ig("POST", f"{uid}/media", token, media_type="STORIES",
                        **({"video_url": url} if video else {"image_url": url}))["id"]
        for _ in range(36 if video else 10):
            s = kanaele._ig("GET", c, token, fields="status_code").get("status_code")
            if s == "FINISHED":
                break
            if s in ("ERROR", "EXPIRED"):
                raise RuntimeError(f"Instagram-Story nicht verarbeitet ({s})")
            warten(10 if video else 3)
        kanaele._ig("POST", f"{uid}/media_publish", token, creation_id=c)
        return "Story geteilt"
    finally:
        datei.unlink(missing_ok=True)
