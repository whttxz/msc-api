from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from ytmusicapi import YTMusic
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

@app.get("/")
def root():
    return {"status": "ok", "message": "Music API is running"}

@app.get("/search")
def search_tracks(q: str = Query(..., description="Поисковый запрос")):
    try:
        results = ytmusic.search(q, filter="songs")
        tracks = []
        for item in results[:15]:
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
    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            stream_url = info.get("url")
            if not stream_url:
                raise HTTPException(status_code=404, detail="Stream URL not found")
            return {
                "id": video_id,
                "title": info.get("title"),
                "stream_url": stream_url
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/playlist")
def get_playlist(playlist_id: str = Query(..., description="ID плейлиста")):
    try:
        if "list=" in playlist_id:
            playlist_id = playlist_id.split("list=")[1].split("&")[0]

        data = ytmusic.get_playlist(playlist_id)
        tracks = []
        for item in data.get("tracks", []):
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
        return {
            "title": data.get("title"),
            "track_count": len(tracks),
            "tracks": tracks
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
