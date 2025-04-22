import asyncio
from contextlib import asynccontextmanager
import dotenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
import nltk
import uvicorn

from api_objects import Digest, Story, Timeline
from fetch import fetch_digest, fetch_latest_digest, fetch_story, fetch_timeline

nltk.download("punkt_tab")
dotenv.load_dotenv()
    
@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(refresh_loop())
    yield
    task.cancel()  # optional: handle shutdown cleanly
    await task

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

latest_digest: Digest | None = None
stories: dict[int, Story] = {}
timelines: dict[int, Timeline] = {}
digests: dict[int, Digest] = {}

async def refresh_loop(new_digest_check_interval: int = 15, refresh_interval: int = 240):
    global latest_digest, stories, timelines, digests
    sleep_1_min = lambda: asyncio.sleep(60)
    i = 0 
    while True:
        if i % new_digest_check_interval == 0:
            print("Fetching latest digest")
            latest_digest = await fetch_latest_digest()
            print(f"Fetched latest digest {latest_digest.id=}")
        if i % refresh_interval == 0:
            stories, timelines, digests = {}, {}, {}
            print("Cleared in-memory stories, timelines, and digests")
        i += 1
        await sleep_1_min()


@app.get("/latest_digest")
async def get_latest_digest() -> Digest:
    return latest_digest


@app.get("/digest/{digest_id}")
async def get_digest(digest_id: int) -> Digest:
    if digest_id in digests:
        return digests[digest_id]
    digest = await fetch_digest(digest_id)
    digests[digest_id] = digest
    return digest


@app.get("/story/{story_id}")
async def get_story(story_id: int) -> Story:
    if story_id in stories:
        return stories[story_id]
    story = await fetch_story(story_id)
    stories[story_id] = story
    return story


@app.get("/timeline/{timeline_id}")
async def get_story(timeline_id: int) -> Timeline:
    if timeline_id in timelines:
        return timelines[timeline_id]
    timeline = await fetch_timeline(timeline_id)
    timelines[timeline_id] = timeline
    return timeline


@app.post("/refresh")
async def run_refresh():
    global latest_digest, stories, timelines, digests
    latest_digest = await fetch_latest_digest()
    stories, timelines, digests = {}, {}, {}
    return "Refreshed successfully"


handler = Mangum(app)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
