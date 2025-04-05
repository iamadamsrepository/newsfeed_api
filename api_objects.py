from dataclasses import dataclass
import datetime as dt

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