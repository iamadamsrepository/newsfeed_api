import asyncio
import datetime as dt
import os
import dotenv
import json
from collections import defaultdict
from dataclasses import dataclass

import nltk
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from nltk.tokenize import sent_tokenize

from db_connection import DBHandler
from db_objects import ArticleRow, ImageRow, ProviderRow, StoryRow

nltk.download("punkt_tab")
dotenv.load_dotenv()


@dataclass
class Provider:
    name: str
    url: str
    favicon_url: str
    country: str


@dataclass
class Image:
    url: str


@dataclass
class Article:
    title: str
    subtitle: str
    date: dt.date
    url: str
    provider: Provider


@dataclass
class Story:
    id: int
    title: str
    ts: dt.datetime
    summary: list[str]
    coverage: list[str]
    articles: list[Article]
    images: list[Image]

    @property
    def n_articles(self) -> int:
        return len(self.articles)

    @property
    def n_providers(self) -> int:
        return len(set(a.provider.name for a in self.articles))

    @property
    def n_countries(self) -> int:
        return len(set(a.provider.country for a in self.articles))


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

ranked_stories: list[Story] = []
stories_by_id: dict[int, Story] = {}


async def fetch_stories() -> tuple[list[Story], dict[int, Story]]:
    db = DBHandler({
        "host": os.getenv("PG_HOST"),
        "port": os.getenv("PG_PORT"),
        "database": os.getenv("PG_DATABASE"),
        "user": os.getenv("PG_USER"),
        "password": os.getenv("PG_PASSWORD"),
    })
    digest_id = db.run_sql("select max(digest_id) from stories")[0][0]
    stories: dict[int, StoryRow] = {
        (sr := StoryRow(*s)).id: sr
        for s in db.run_sql(
            f"""
        select s.*
        from stories s
        where s.digest_id = {digest_id}
        """
        )
    }
    providers: dict[int, ProviderRow] = {
        (pr := ProviderRow(*p)).id: pr
        for p in db.run_sql(
            """
        select p.*
        from providers p
        """
        )
    }
    db_out = db.run_sql(
        f"""
        select s.id, a.*
        from stories s
        left join story_articles sa
        on s.id = sa.story_id
        left join articles a
        on sa.article_id = a.id
        where s.digest_id = {digest_id}
        """
    )
    story_articles: dict[int, list[ArticleRow]] = defaultdict(list)
    for row in db_out:
        story_articles[row[0]].append(ArticleRow(*row[1:]))
    db_out = db.run_sql(
        f"""
        select s.id, i.*
        from stories s
        left join images i
        on s.id = i.story_id
        where s.digest_id = {digest_id}
        """
    )
    story_images: dict[int, list[ImageRow]] = defaultdict(list)
    for row in db_out:
        story_images[row[0]].append(ImageRow(*row[1:]))

    for story in stories.values():
        story_articles[story.id] = sorted(story_articles[story.id], key=article_ranking_criterion, reverse=True)

    stories_list = []
    stories_by_id = {}
    for story_out in stories.values():
        story_out: StoryRow
        story = Story(
            id=story_out.id,
            title=story_out.title,
            ts=story_out.ts,
            summary=sent_tokenize(story_out.summary),
            coverage=sent_tokenize(story_out.coverage),
            articles=[
                Article(
                    title=article.title,
                    subtitle=article.subtitle,
                    date=article.date,
                    url=article.url,
                    provider=Provider(
                        name=providers[article.provider_id].name,
                        url=providers[article.provider_id].url,
                        favicon_url=providers[article.provider_id].favicon_url,
                        country=providers[article.provider_id].country,
                    ),
                )
                for article in story_articles[story_out.id]
            ],
            images=[Image(url=image.url) for image in story_images[story_out.id]],
        )
        stories_list.append(story)
        stories_by_id[story_out.id] = story
    ranked_stories = sorted(stories_list, key=story_ranking_criterion, reverse=True)
    return ranked_stories, stories_by_id


def article_ranking_criterion(article: ArticleRow) -> float:
    return article.ts


def story_ranking_criterion(story: Story) -> float:
    return story.n_providers * story.n_articles


async def fetch_stories_loop():
    global ranked_stories, stories_by_id
    while True:
        ranked_stories, stories_by_id = await fetch_stories()
        print("Fetched stories")
        await asyncio.sleep(600)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(fetch_stories_loop())


@app.get("/stories")
async def get_stories() -> list[Story]:
    return ranked_stories


@app.get("/story/{story_id}")
async def get_story(story_id: int) -> Story:
    return stories_by_id.get(story_id)


@app.post("/refresh")
async def run_fetch_stories():
    global ranked_stories, stories_by_id
    ranked_stories, stories_by_id = await fetch_stories()
    return {"message": "stories refreshed successfully"}


handler = Mangum(app)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
