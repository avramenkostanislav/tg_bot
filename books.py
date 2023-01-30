from datetime import datetime
from dataclasses import dataclass

import aiosqlite
import config

def _chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

@dataclass
class Book:
    id: int
    name: str
    category_name: str
    read_start: datetime
    read_finish: datetime


@dataclass
class Category:
    id: int
    books: list[Book]


async def get_all_books(chunk_size: int | None):
    books = []
    async with aiosqlite.connect(config.SQLITE_DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
                            select b.id as book_id
	                              ,b.name as book_name
	                              ,b.read_start
	                              ,b.read_finish
	                              ,bc.id as category_id
	                              ,bc.name as category_name
                            from book as b 
	                            left join book_category bc
		                            on b.category_id =bc.id
                            order by bc.ordering, b.ordering;
                            """) as cursor:
             async for row in cursor:
                 books.append(Book(
                     id=row["book_id"],
                     name=row["book_name"],
                     category_name=row["category_name"],
                     read_start=row["read_start"],
                     read_finish=row["read_finish"]
                 ))
    if chunk_size:
        return _chunks(books, chunk_size)
    return books
