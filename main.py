from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from ytmusicapi import YTMusic
import urllib.request
import json
import yt_dlp

app = FastAPI(title="Music API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ytmusic = YTMusic()

PIPED_INSTANCES = [
    "https://pipedapi.kavin.rocks",
    "https://pipedapi.tokhmi.xyz",
    "https://pipedapi.moomoo.me",
]

@app.get("/")
def root():
    return {"status": "ok", "message": "Music API is running"}

@app.get("/search")
def search_tracks(q: str = Query(..., description="Поисковый запрос")):
    try:
        results = ytmusic.search(q, filter="songs")
        tracks = []
        for item in results[:20]:
            video_id = item.get("videoId")
            if not video_id:
                continue
            artists = ", ".join([a["name"] for a in item.get("artists", [])])
            thumbnails = item.get("thumbnails", [])
            cover = thumbnails[-1]["url"] if thumbnails else None
            tracks.append({
                "id": video_id,
                "title": item.get("title"),
                "artist": artists,
                "duration": item.get("duration"),
                "cover": cover
            })
        return {"results": tracks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stream/{video_id}")
def get_stream_url(video_id: str):
    # Попытка 1: yt-dlp с обходом через мобильные клиенты iOS/Android
    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'android_vr', 'web']
            }
        }
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            stream_url = info.get("url")
            if stream_url:
                return {
                    "id": video_id,
                    "title": info.get("title"),
                    "stream_url": stream_url
                }
    except Exception:
        pass

    # Попытка 2: резерв через Piped API
    for instance in PIPED_INSTANCES:
        try:
            req = urllib.request.Request(
                f"{instance}/streams/{video_id}",
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            with urllib.request.urlopen(req, timeout=6) as response:
                data = json.loads(response.read().decode())
                streams = data.get("audioStreams", [])
                if streams:
                    best = sorted(streams, key=lambda x: x.get("bitrate", 0), reverse=True)[0]
                    return {
                        "id": video_id,
                        "title": data.get("title", ""),
                        "stream_url": best["url"]
                    }
        except Exception:
            continue

    raise HTTPException(status_code=404, detail="Stream not available")
