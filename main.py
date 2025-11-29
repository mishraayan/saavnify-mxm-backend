from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from musicxmatch_api import MusixMatchAPI
import re

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
        queries: list[str] = []

        if title and artist:
            # full combination first
            queries.append(f"{title} {artist}")

            # also try only main artist before comma / & / feat / ft.
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

            # 🔍 Normalize result into a track_list
            track_list = []

            if isinstance(search, dict):
                # typical musixmatch-style nested dict
                msg = search.get("message") or {}
                body = msg.get("body") or {}
                if isinstance(body, dict):
                    track_list = body.get("track_list", [])
                elif isinstance(body, list):
                    track_list = body
            elif isinstance(search, list):
                # library might already return a plain list of tracks
                track_list = search

            if not track_list:
                continue

            # Take first element & unwrap "track" if present
            first = track_list[0]
            if isinstance(first, dict) and "track" in first:
                first = first["track"]

            if not isinstance(first, dict):
                continue

            track_id = first.get("track_id") or first.get("id")
            if track_id:
                break

        if not track_id:
            raise HTTPException(status_code=404, detail="No track found")

        # 3️⃣ Fetch lyrics for that track_id
        res = mxm.get_track_lyrics(track_id=track_id)
        body = res.get("message", {}).get("body", {})
        lyrics_obj = body.get("lyrics", {})
        lyrics_body = lyrics_obj.get("lyrics_body", "")

        if not lyrics_body:
            raise HTTPException(status_code=404, detail="No lyrics")

        cleaned = lyrics_body.split("*******")[0].strip()
        if not cleaned:
            raise HTTPException(status_code=404, detail="No usable lyrics")

        return {"lyrics": cleaned}

    except HTTPException:
        # re-raise the specific HTTP error (400/404 etc.)
        raise
    except Exception as e:
        print("MXM error:", repr(e))
        # treat unknown issues as "no lyrics" instead of hard 500
        raise HTTPException(status_code=404, detail="No lyrics available")
