from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from musicxmatch_api import MusixMatchAPI

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

mxm = MusixMatchAPI()


@app.get("/mxm-lyrics")
async def get_lyrics(
    title: str = Query(..., description="Song title"),
    artist: str | None = Query(None, description="Artist name"),
):
    if not title:
        raise HTTPException(status_code=400, detail="Title is required")

    try:
        title = title.strip()
        artist = (artist or "").strip()

        # 1️⃣ Build search queries in order of preference
        queries = []

        if title and artist:
            queries.append(f"{title} {artist}")  # full
            # also try only main artist before comma / feat
            import re

            primary_artist = re.split(
                r",|&|feat\.|ft\.", artist, flags=re.IGNORECASE
            )[0].strip()
            if primary_artist and primary_artist.lower() != artist.lower():
                queries.append(f"{title} {primary_artist}")

        # Always try plain title as well
        queries.append(title)

        track_id = None

        # 2️⃣ Try each query until one returns a track
        for q in queries:
            print("🔎 MXM search query:", q)
            search = mxm.search_tracks(q)
            track_list = search["message"]["body"].get("track_list", [])
            if track_list:
                track_id = track_list[0]["track"]["track_id"]
                break

        if not track_id:
            raise HTTPException(status_code=404, detail="No track found")

        # 3️⃣ Fetch lyrics for that track_id
        res = mxm.get_track_lyrics(track_id=track_id)
        lyrics_obj = res["message"]["body"].get("lyrics", {})
        lyrics_body = lyrics_obj.get("lyrics_body", "")

        if not lyrics_body:
            raise HTTPException(status_code=404, detail="No lyrics")

        cleaned = lyrics_body.split("*******")[0].strip()
        if not cleaned:
            raise HTTPException(status_code=404, detail="No usable lyrics")

        return {"lyrics": cleaned}

    except HTTPException:
        raise
    except Exception as e:
        print("MXM error:", repr(e))
        # treat unknown issues as "no lyrics" instead of hard 500
        raise HTTPException(status_code=404, detail="No lyrics available")
