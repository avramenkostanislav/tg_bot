from datetime import datetime
from dataclasses import dataclass
import logging
import aiosqlite
from books import Book
import config

from typing import Iterable
from users import _insert_user

@dataclass
class BookVoteResult:
    book_name: str
    score: int

@dataclass
class Voting:
    id: int
    voting_start: str
    voting_finish: str

    def __post_init__(self):
        """Set up read_start and read_finish to needed string format"""
        for field in ("voting_start", "voting_finish"):
            value = getattr(self, field)
            if value is None: continue
            try:
                value = datetime.strptime(value, "%Y-%m-%d").strftime(config.DATE_FORMAT)
            except ValueError:
                continue
            setattr(self, field, value)

@dataclass
class VoteResult:
    voting: Voting
    leaders: list[BookVoteResult]



logger = logging.getLogger(__name__)

async def get_actual_voting() -> Voting | None:
    sql = """
        select id, voting_start, voting_finish
        from voting
        where voting_start <= current_date
        and voting_finish >= current_date
        order by voting_start
        limit 1"""
    async with aiosqlite.connect(config.SQLITE_DB_FILE) as db:
        db.row_factory=aiosqlite.Row
        async with db.execute(sql) as cursor:
            row = await cursor.fetchone()
            if row is None: return None
            return Voting (
                id = row["id"],
                voting_start = row["voting_start"],
                voting_finish = row["voting_finish"]
            )


async def save_vote(telegram_user_id: int, books: Iterable[Book]) -> None:
    await _insert_user(telegram_user_id)
    actual_voting = await get_actual_voting()
    if actual_voting is None:
        logger.warning("No actual voting in save_vote()")
        return
    sql = """
        insert or replace into vote (
                        vote_id,
                        user_id,
                        first_book_id,
                        second_book_id,
                        third_book_id)
                    values (:vote_id,
                            :user_id,
                            :first_book_id,
                            :second_book_id,
                            :third_book_id)"""
    books = tuple(books)
    async with aiosqlite.connect(config.SQLITE_DB_FILE) as db:
        await db.execute(sql, {
            "vote_id": actual_voting.id,
            "user_id": telegram_user_id,
            "first_book_id": books[0].id,
            "second_book_id": books[1].id,
            "third_book_id": books[2].id
        })
        await db.commit()

async def get_leaders() -> VoteResult | None:
    actual_voting = await get_actual_voting()
    if actual_voting is None: return None
    vote_results = VoteResult(
            voting = Voting(
            voting_start=actual_voting.voting_start,
            voting_finish=actual_voting.voting_finish,
            id=actual_voting.id
        ),
        leaders = []
    )
    sql = """
    select t2.*, b.name as book_name 
    from (select t.book_id, sum(t.score) as score
    from (
        select first_book_id as book_id, 3*count(*) as score
        from vote v
        where vote_id=(:voting_id)
        group by first_book_id
        
        union
        
        select second_book_id as book_id, 2*count(*) as score
        from vote v
        where vote_id=(:voting_id)
        group by second_book_id
        
        union
        
        select third_book_id as book_id, 2*count(*) as score
        from vote v
        where vote_id=(:voting_id)
        group by third_book_id
    ) t
    group by t.book_id
    order by sum(t.score) desc
    limit 10) t2
    left join book b 
      on b.id=t2.book_id
    """
    async with aiosqlite.connect(config.SQLITE_DB_FILE) as db:
        db.row_factory=aiosqlite.Row
        async with db.execute(sql, {"voting_id": actual_voting.id}) as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                vote_results.leaders.append(BookVoteResult(
                    book_name = row["book_name"],
                    score = row["score"]
                ))
    return vote_results
