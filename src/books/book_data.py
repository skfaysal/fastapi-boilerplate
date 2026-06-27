book_store = {
    1: {"id": 1, "title": "Clean Code", "author": "Robert C. Martin", "year": 2008, "price": 35.99},
    2: {"id": 2, "title": "The Pragmatic Programmer", "author": "David Thomas", "year": 1999, "price": 42.00},
    3: {"id": 3, "title": "Fluent Python", "author": "Luciano Ramalho", "year": 2022, "price": 59.99},
    4: {"id": 4, "title": "Designing Data-Intensive Applications", "author": "Martin Kleppmann", "year": 2017, "price": 55.00},
    5: {"id": 5, "title": "You Don't Know JS", "author": "Kyle Simpson", "year": 2015, "price": 29.99},
}

_next_id = 6


def next_id() -> int:
    global _next_id
    current = _next_id
    _next_id += 1
    return current
