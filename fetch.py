from collections import defaultdict
import os

from api_objects import Digest, Story, Timeline
from db_connection import DBHandler
from db_objects import ArticleRow, DigestRow, ImageRow, ProviderRow, StoryRow, TimelineEventRow, TimelineRow


def get_db_connection() -> DBHandler:
    return DBHandler({
        "host": os.getenv("PG_HOST"),
        "port": os.getenv("PG_PORT"),
        "database": os.getenv("PG_DATABASE"),
        "user": os.getenv("PG_USER"),
        "password": os.getenv("PG_PASSWORD"),
    })


async def fetch_story(story_id: int) -> Story:
    db = get_db_connection()
    db_out = db.run_sql(
        f"""
        select s.*
        from stories s
        where s.id = {story_id}
        """
    )
    if not db_out:
        return None
    story = StoryRow(*db_out[0])
    providers: dict[int, ProviderRow] = {
        (pr := ProviderRow(*p)).id: pr
        for p in db.run_sql(
            """
        select p.*
        from providers p
        """
        )
    }
    articles = [ArticleRow(*row) for row in db.run_sql(
        f"""
        select a.*
        from articles a
        left join story_articles sa
        on a.id = sa.article_id
        where sa.story_id = {story_id}
        """
    )]
    images = [ImageRow(*row) for row in db.run_sql(
        f"""
        select i.*
        from images i
        where i.story_id = {story_id}
        """
    )]
    return Story.from_db_rows(story, articles, images, providers)


async def fetch_timeline(timeline_id: int) -> Timeline:
    db = get_db_connection()
    db_out = db.run_sql(
        f"""
        select t.*
        from timelines t
        where t.id = {timeline_id}
        """
    )
    if not db_out:
        return None
    timeline = TimelineRow(*db_out[0])
    stories = [StoryRow(*row) for row in db.run_sql(
        f"""
        select s.*
        from stories s
        left join timeline_stories ts
        on s.id = ts.story_id
        where ts.timeline_id = {timeline_id}
        """
    )]
    events = [TimelineEventRow(*row) for row in db.run_sql(
        f"""
        select te.*
        from timeline_events te
        where te.timeline_id = {timeline_id}
        """
    )]
    return Timeline.from_db_rows(timeline, events, stories)


async def fetch_digest(digest_id: int) -> Digest:
    db = get_db_connection()
    db_out = db.run_sql(
        f"""
        select d.*
        from digests d
        where d.id = {digest_id}
        """
    )
    if not db_out:
        return None
    digest = DigestRow(*db_out[0])
    timelines = [TimelineRow(*row) for row in db.run_sql(
        f"""
        select t.*
        from timelines t
        where t.digest_id = {digest_id}
        """
    )]
    timeline_events: dict[int, list[TimelineEventRow]] = defaultdict(list)
    for row in db.run_sql(
        f"""
        select te.*
        from timeline_events te
        left join timelines t
        on te.timeline_id = t.id
        where t.digest_id = {digest_id}
        """
    ):
        timeline_events[row[0]].append(TimelineEventRow(*row))
    timeline_stories: dict[int, list[StoryRow]] = defaultdict(list)
    for row in db.run_sql(
        f"""
        select t.id, s.*
        from stories s
        left join timeline_stories ts
        on s.id = ts.story_id
        left join timelines t
        on ts.timeline_id = t.id
        where t.digest_id = {digest_id}
        """
    ):
        timeline_stories[row[0]].append(StoryRow(*row[1:]))
    stories: list[StoryRow] = [
        StoryRow(*row) for row in db.run_sql(
            f"""
            select s.*
            from stories s
            where s.digest_id = {digest_id}
            """
        )
    ]
    story_articles: dict[int, list[ArticleRow]] = defaultdict(list)
    for row in db.run_sql(
            f"""
            select s.id, a.*
            from stories s
            left join story_articles sa
            on s.id = sa.story_id
            left join articles a
            on sa.article_id = a.id
            where s.digest_id = {digest_id}
            """
    ):
        story_articles[row[0]].append(ArticleRow(*row[1:]))
    story_images: dict[int, list[ImageRow]] = defaultdict(list)
    for row in db.run_sql(
            f"""
            select s.id, i.*
            from stories s
            left join images i
            on s.id = i.story_id
            where s.digest_id = {digest_id}
            """
    ):
        story_images[row[0]].append(ImageRow(*row[1:]))
    providers: dict[int, ProviderRow] = {
        (pr := ProviderRow(*p)).id: pr
        for p in db.run_sql(
            """
        select p.*
        from providers p
        """
        )
    }

    return Digest.from_db_rows(
        digest,
        timelines,
        timeline_events,
        timeline_stories,
        stories,
        story_articles,
        story_images,
        providers
    )

async def fetch_latest_digest() -> Digest:
    db = get_db_connection()
    db_out = db.run_sql(
        f"""
        select d.*
        from digests d
        where d.status = 'READY'
        order by d.ts desc
        limit 1
        """
    )
    if not db_out:
        return None
    digest = DigestRow(*db_out[0])
    return await fetch_digest(digest.id)
