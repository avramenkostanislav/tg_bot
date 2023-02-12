from datetime import datetime
from dataclasses import dataclass
from typing import Iterable, Literal

import aiosqlite
import config


@dataclass
class Book:
    id: int
    name: str
    category_id: int
    category_name: str
    read_start: str | None
    read_finish: str | None

    def __post_init__(self):
        """Set up read_start and read_finish to needed string format"""
        for field in ("read_start", "read_finish"):
            value = getattr(self, field)
            if value is None: continue
            value = datetime.strptime(value, "%Y-%m-%d").strftime(config.DATE_FORMAT)
            setattr(self, field, value)


@dataclass
class Category:
    id: int
    name: str
    books: Iterable[Book]

async def get_all_books() -> Iterable[Category]:
    sql = _get_books_base_sql() + """
        order by bc.ordering, b.ordering;
    """
    books = await _get_books_from_db(sql)
    #books = []
    # async with aiosqlite.connect(config.SQLITE_DB_FILE) as db:
    #     db.row_factory = aiosqlite.Row
    #     async with db.execute(sql) as cursor:
    #          async for row in cursor:
    #              books.append(Book(
    #                  id=row["book_id"],
    #                  name=row["book_name"],
    #                  category_id=row["category_id"],
    #                  category_name=row["category_name"],
    #                  read_start=row["read_start"],
    #                  read_finish=row["read_finish"]
    #              ))
    return _group_books_by_categories(books)

async def get_not_started_books() -> Iterable[Category]:
    sql = _get_books_base_sql() + """
        where b.read_start is null
        order by bc.ordering, b.ordering;
    """
    books = await _get_books_from_db(sql)
    return _group_books_by_categories(books)


async def get_already_read_books() -> Iterable[Book]:
    sql = _get_books_base_sql() + """ 
        where read_start < current_date	
	        and read_finish <= current_date
	    order by b.read_start;
    """
    return await _get_books_from_db(sql)

async def get_now_reading_book() -> Iterable[Book]:
    sql = _get_books_base_sql() + """
            where read_start <= current_date	
    	        and read_finish >= current_date
    	    order by b.read_start;
        """
    return await _get_books_from_db(sql)

async def get_books_by_numbers(numbers: Iterable[int]) -> Iterable[Book]:
    numbers_joined = ", ".join(map(str, map(int, numbers)))

    hardcoded_sql_values = []
    for index, number in enumerate(numbers, 1):
        hardcoded_sql_values.append(f"({number}, {index})")

    output_hardcoded_sql_values = ", ".join(hardcoded_sql_values)

    sql = f"""
        select t2.* from (
            values {output_hardcoded_sql_values}
        ) t0
        inner join
        (
        select t.* from (
            {_get_books_base_sql('row_number() over (order by bc."ordering", b."ordering") as idx')}
        where read_start is null
        ) t
        where t.idx in ({numbers_joined})
        ) t2
        on t0.column1=t2.idx
        order by t0.column2
    """
    books = await _get_books_from_db(sql)
    return books

def _group_books_by_categories(books: Iterable[Book]) -> Iterable[Category]:
    categories = []
    category_id = None
    for book in books:
        if category_id != book.category_id:
            categories.append(Category(
                id=book.category_id,
                name=book.category_name,
                books=[book])
            )
            category_id = book.category_id
            continue
        categories[-1].books.append(book)
    return categories

# def _get_books_base_sql(select_param: Literal[str] | None = None) -> Literal[str]:
#     return f"""
#         SELECT
#             b.id as book_id,
#             b.name as book_name,
#             bc.id as category_id,
#             bc.name as category_name,
#             {select_param + "," if select_param else ""}
#             b.read_start, b.read_finish,
#             read_comments
#         FROM book b
#         LEFT JOIN book_category bc ON bc.id=b.category_id
#     """

def _get_books_base_sql(select_param: Literal[str] | None = None) -> Literal[str]:
    return f"""
        select b.id as book_id
              ,b.name as book_name
              ,bc.id as category_id
              ,bc.name as category_name
              ,{select_param + "," if select_param else ""}
              b.read_start
              ,b.read_finish
        from book b
          left join book_category bc
            on b.category_id =bc.id
        """


async def _get_books_from_db(sql: Literal[str]) -> Iterable[Book]:
    books = []
    async with aiosqlite.connect(config.SQLITE_DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(sql) as cursor:
            async for row in cursor:
                books.append(Book(
                    id=row["book_id"],
                    name=row["book_name"],
                    category_id=row["category_id"],
                    category_name=row["category_name"],
                    read_start=row["read_start"],
                    read_finish=row["read_finish"]
                ))
    return books


