import asyncio
from contextlib import asynccontextmanager
import dotenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
import nltk
import uvicorn

from api_objects import Story
from fetch import fetch_stories, fetch_story

nltk.download("punkt_tab")
dotenv.load_dotenv()
    
@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(fetch_stories_loop())
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

ranked_stories: list[Story] = []
stories_by_id: dict[int, Story] = {}

async def fetch_stories_loop():
    global ranked_stories, stories_by_id
    while True:
        ranked_stories, stories_by_id = await fetch_stories()
        print("Fetched stories")
        await asyncio.sleep(1800)


@app.get("/stories")
async def get_stories() -> list[Story]:
    return ranked_stories


@app.get("/story/{story_id}")
async def get_story(story_id: int) -> Story:
    if story_id in stories_by_id:
        return stories_by_id[story_id]
    story = await fetch_story(story_id)
    stories_by_id[story_id] = story
    return story


@app.post("/refresh")
async def run_fetch_stories():
    global ranked_stories, stories_by_id
    ranked_stories, stories_by_id = await fetch_stories()
    return {"message": "stories refreshed successfully"}


handler = Mangum(app)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
