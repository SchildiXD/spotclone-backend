from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx

app = FastAPI(title="SpotClone Backend (Piped)")

# CORS erlauben, damit die Android-App später Anfragen stellen darf
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Piped-Instanz, die du nutzen möchtest
PIPED_API_BASE = "https://pipedapi.leptons.xyz"

@app.get("/health")
def health_check():
    """Endpunkt für Render, um zu prüfen, ob der Server lebt."""
    return {"status": "alive", "app": "SpotClone"}

@app.get("/stream/{video_id}")
async def get_audio_stream(video_id: str):
    """
    Nimmt eine YouTube-Video-ID, fragt Piped und gibt die beste Audio-Stream-URL zurück.
    """
    url = f"{PIPED_API_BASE}/streams/{video_id}"

    async with httpx.AsyncClient() as client:
        resp = await client.get(url)

    if resp.status_code != 200:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"Piped-Fehler: {resp.status_code} {resp.text}",
        )

    data = resp.json()

    audio_streams = data.get("audioStreams", [])
    if not audio_streams:
        raise HTTPException(status_code=404, detail="Kein Audio-Stream bei Piped gefunden")

    # Sortiere nach Bitrate (höchste zuerst) und nimm den besten Stream
    best_audio = sorted(audio_streams, key=lambda s: s.get("bitrate", 0), reverse=True)[0]

    return {
        "url": best_audio["url"],
        "format": best_audio.get("format", "unknown"),
        "bitrate": best_audio.get("bitrate", 0),
        "title": data.get("title", "Unknown"),
        "thumbnail": data.get("thumbnailUrl", ""),
    }
