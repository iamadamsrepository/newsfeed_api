from dataclasses import dataclass
import datetime as dt

from nltk.tokenize import sent_tokenize

from db_objects import ArticleRow, ImageRow, ProviderRow, StoryRow, TimelineEventRow, TimelineRow

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
    
    @classmethod
    def from_db_rows(cls, story: StoryRow, articles: list[ArticleRow], images: list[ImageRow], providers: dict[int, ProviderRow]) -> "Story":
        return cls(
            id=story.id,
            title=story.title,
            ts=story.ts,
            summary=sent_tokenize(story.summary),
            coverage=sent_tokenize(story.coverage),
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
                for article in articles
            ],
            images=[Image(url=image.url) for image in images],
        )


@dataclass
class StorySummary:
    id: int
    title: str
    ts: dt.datetime
    summary: str
    coverage: str


@dataclass
class TimelineEvent:
    story_id: int
    description: str
    date: dt.date
    date_type: str


@dataclass
class Timeline:
    id: int
    ts: dt.datetime
    subject: str
    headline: str
    summary: str
    events: list[TimelineEvent]
    stories: list[StorySummary]

    @property
    def n_events(self) -> int:
        return len(self.events)
    
    @property
    def n_stories(self) -> int:
        return len(self.story_ids)
    
    @classmethod
    def from_db_rows(cls, timeline: TimelineRow, events: list[TimelineEventRow], stories: list[StoryRow]) -> "Timeline":
        return cls(
            id=timeline.id,
            ts=timeline.ts,
            subject=timeline.subject,
            headline=timeline.headline,
            summary=timeline.summary,
            events=[
                TimelineEvent(
                    story_id=event.story_id,
                    description=event.description,
                    date=event.date,
                    date_type=event.date_type,
                )
                for event in events
            ],
            stories=[
                StorySummary(
                    id=story.id,
                    title=story.title,
                    ts=story.ts,
                    summary=story.summary,
                    coverage=story.coverage,
                )
                for story in stories
            ],
        )
