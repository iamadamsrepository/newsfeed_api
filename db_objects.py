import datetime as dt
from dataclasses import dataclass


@dataclass
class ProviderRow:
    id: int
    name: str
    url: str
    favicon_url: str
    country: str


@dataclass
class ArticleRow:
    id: int
    ts: dt.datetime
    provider_id: int
    title: str
    subtitle: str
    url: str
    body: str
    image_url: str
    image_urls: str
    date: dt.date


@dataclass
class ImageRow:
    id: int
    story_id: int
    url: str
    source_page: str
    height: int
    width: int
    format: str
    title: str


@dataclass
class StoryRow:
    id: int
    ts: dt.datetime
    title: str
    summary: str
    coverage: str
    digest_id: int
    digest_description: str
