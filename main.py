from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
from typing import Optional

app = FastAPI(title="SpotClone Backend (Invidious)")

# CORS erlauben, damit die Android-App später Anfragen stellen darf
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # in Produktion besser auf deine App-URL einschränken
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Wähle eine öffentliche Invidious-Instanz aus der offiziellen Liste:
# https://docs.invidious.io/instances
INVIDIOUS_API_BASE = "https://inv.nadeko.net"

@app.get("/health")
def health_check():
    """Endpunkt für Render, um zu prüfen, ob der Server lebt."""
    return {"status": "alive", "app": "SpotClone", "backend": "invidious"}

@app.get("/stream/{video_id}")
async def get_audio_stream(video_id: str):
    """
    Nimmt eine YouTube-Video-ID, fragt Invidious und gibt die beste Audio-Stream-URL zurück.
    Nutzt ?local=true, damit die Invidious-Instanz als Proxy fungiert (verhindert 403/CORS).
    """
    url = f"{INVIDIOUS_API_BASE}/api/v1/videos/{video_id}"
    params = {"local": "true"}  # wichtig für proxy-URLs

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params)

    if resp.status_code != 200:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"Invidious-Fehler: {resp.status_code} {resp.text}",
        )

    data = resp.json()

    # adaptiveFormats enthält alle Audio+Video-Streams
    adaptive_formats = data.get("adaptiveFormats", [])
    if not adaptive_formats:
        raise HTTPException(status_code=404, detail="Kein adaptiveFormats bei Invidious gefunden")

    # Wir suchen nur Audio-Streams (type enthält "audio")
    audio_formats = [
        f for f in adaptive_formats
        if "audio" in (f.get("type") or "").lower() and f.get("url")
    ]

    if not audio_formats:
        # Fallback: nimm einfach den ersten Stream, falls kein Audio-only erkannt wird
        audio_formats = [f for f in adaptive_formats if f.get("url")]

    if not audio_formats:
        raise HTTPException(status_code=404, detail="Kein Audio-Stream bei Invidious gefunden")

    # Nimm den besten Audio-Stream (nach bitrate sortieren)
    best_audio = max(audio_formats, key=lambda f: int(f.get("bitrate", "0") or "0"))

    return {
        "url": best_audio["url"],
        "format": best_audio.get("container", "unknown"),
        "bitrate": best_audio.get("bitrate", "0"),
        "title": data.get("title", "Unknown"),
        "thumbnail": (
            data.get("videoThumbnails", [{}])[0].get("url", "")
            if data.get("videoThumbnails")
            else ""
        ),
    }