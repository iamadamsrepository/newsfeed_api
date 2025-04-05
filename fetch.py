from collections import defaultdict
import os

from api_objects import Story
from db_connection import DBHandler
from db_objects import ArticleRow, ImageRow, ProviderRow, StoryRow

def article_ranking_criterion(article: ArticleRow) -> float:
    return article.ts


def story_ranking_criterion(story: Story) -> float:
    return story.n_providers * story.n_articles


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

async def fetch_stories() -> tuple[list[Story], dict[int, Story]]:
    db = get_db_connection()
    digest_id = db.run_sql("select max(id) from digests")[0][0]
    # digest_ts = db.run_sql(f"select ts from digest where id = {digest_id}")[0][0]
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
        story =  Story.from_db_rows(
            story_out,
            story_articles[story_out.id],
            story_images[story_out.id],
            providers,
        )
        stories_list.append(story)
        stories_by_id[story_out.id] = story
    ranked_stories = sorted(stories_list, key=story_ranking_criterion, reverse=True)
    return ranked_stories, stories_by_id