from dataclasses import dataclass
import datetime as dt

from nltk.tokenize import sent_tokenize

from db_objects import ArticleRow, DigestRow, ImageRow, ProviderRow, StoryRow, TimelineEventRow, TimelineRow


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
    summary: list[str]
    events: list[TimelineEvent]
    stories: list[StorySummary]

    @property
    def n_events(self) -> int:
        return len(self.events)
    
    @property
    def n_stories(self) -> int:
        return len(self.stories)
    
    @classmethod
    def from_db_rows(cls, timeline: TimelineRow, events: list[TimelineEventRow], stories: list[StoryRow]) -> "Timeline":
        return cls(
            id=timeline.id,
            ts=timeline.ts,
            subject=timeline.subject,
            headline=timeline.headline,
            summary=sent_tokenize(timeline.summary),
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

@dataclass
class Digest:
    id: int
    ts: dt.datetime
    stories: list[Story]
    timelines: list[Timeline]

    @classmethod
    def from_db_rows(
        cls, 
        digest: DigestRow, 
        timelines: list[TimelineRow], 
        timeline_events: dict[int, list[TimelineEventRow]], 
        timeline_stories: dict[int, list[StoryRow]],
        stories: list[StoryRow], 
        story_articles: dict[int, list[ArticleRow]], 
        story_images: dict[int, list[ImageRow]],
        providers: dict[int, ProviderRow]
    ) -> "Digest":
        story_articles = {
            story_id: sort_articles(articles)
            for story_id, articles in story_articles.items()
        }
        stories = [
            Story.from_db_rows(
                story,
                story_articles[story.id],
                story_images[story.id],
                providers
            )
            for story in stories
        ]
        stories = sort_stories(stories)
        timelines = [
            Timeline.from_db_rows(
                timeline,
                timeline_events[timeline.id],
                timeline_stories[timeline.id]
            )
            for timeline in timelines
        ]
        timelines = sort_timelines(timelines)
        return cls(
            id=digest.id,
            ts=digest.ts,
            stories=stories,
            timelines=timelines,
        )
        
def article_ranking_criterion(article: ArticleRow) -> float:
    return article.ts


def sort_articles(articles: list[ArticleRow]) -> list[ArticleRow]:
    return sorted(articles, key=article_ranking_criterion, reverse=True)


def story_ranking_criterion(story: Story) -> float:
    return story.n_providers * story.n_articles


def sort_stories(stories: list[Story]) -> list[Story]:
    return sorted(stories, key=story_ranking_criterion, reverse=True)


def timeline_ranking_criterion(timeline: Timeline) -> float:
    return timeline.n_stories * timeline.n_events


def sort_timelines(timelines: list[Timeline]) -> list[Timeline]:
    return sorted(timelines, key=timeline_ranking_criterion, reverse=True)
