from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from musicxmatch_api import MusixMatchAPI

app = FastAPI()

# ✅ CORS so your React app can call this from any domain (you can restrict later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # or ["https://your-frontend.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Single shared client
mxm = MusixMatchAPI()


@app.get("/mxm-lyrics")
async def get_lyrics(
    title: str = Query(..., description="Song title"),
    artist: str | None = Query(None, description="Artist name"),
):
    """
    Example:
    GET /mxm-lyrics?title=Kesariya&artist=Arijit+Singh
    → { "lyrics": "..." }
    """
    if not title:
        raise HTTPException(status_code=400, detail="Title is required")

    try:
        # 1️⃣ Search track on Musixmatch
        query = f"{title} {artist}" if artist else title
        search = mxm.search_tracks(query)
        track_list = search["message"]["body"].get("track_list", [])
        if not track_list:
            raise HTTPException(status_code=404, detail="No track found")

        track_id = track_list[0]["track"]["track_id"]

        # 2️⃣ Get lyrics for that track
        res = mxm.get_track_lyrics(track_id=track_id)
        lyrics_obj = (
            res["message"]["body"]
            .get("lyrics", {})
        )
        lyrics_body = lyrics_obj.get("lyrics_body", "")

        if not lyrics_body:
            raise HTTPException(status_code=404, detail="No lyrics")

        # Musixmatch usually appends disclaimer lines at the end → cut them
        cleaned = lyrics_body.split("*******")[0].strip()

        if not cleaned:
            raise HTTPException(status_code=404, detail="No usable lyrics")

        return {"lyrics": cleaned}

    except HTTPException:
        raise
    except Exception as e:
        print("MXM error:", e)
        raise HTTPException(status_code=500, detail="Internal error")
