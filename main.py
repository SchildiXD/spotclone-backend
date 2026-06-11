from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp

app = FastAPI(title="SpotClone Backend")

# CORS erlauben, damit die Android-App später Anfragen stellen darf
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    """Endpunkt für Render, um zu prüfen, ob der Server lebt."""
    return {"status": "alive", "app": "SpotClone"}

@app.get("/stream/{video_id}")
def get_audio_stream(video_id: str):
    """
    Nimmt eine YouTube Video ID und gibt die direkte Audio-Stream-URL zurück.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    # yt-dlp Optionen
    ydl_opts = {
        'format': 'bestaudio/best', # Nur Audio
        'quiet': True,
        'no_warnings': True,
        # Versucht, YouTube's Drosselung für Server-IPs zu umgehen
        'extractor_args': {'youtube': {'player_client': ['web']}},
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Filtere nur Audio-Formate heraus (kein Video)
            audio_formats = [
                f for f in info['formats'] 
                if f.get('acodec') != 'none' and f.get('vcodec') == 'none' and f.get('url')
            ]

            if not audio_formats:
                raise HTTPException(status_code=404, detail="Kein Audio-Stream gefunden")

            # Sortiere nach Bitrate und nimm den besten Stream
            best_audio = sorted(audio_formats, key=lambda x: x.get('abr', 0), reverse=True)[0]

            return {
                "url": best_audio['url'],
                "format": best_audio.get('ext', 'unknown'),
                "bitrate": best_audio.get('abr', 0),
                "title": info.get('title', 'Unknown'),
                "thumbnail": info.get('thumbnail', '')
            }

    except yt_dlp.utils.DownloadError as e:
        raise HTTPException(status_code=404, detail=f"Video nicht gefunden: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Serverfehler: {str(e)}")