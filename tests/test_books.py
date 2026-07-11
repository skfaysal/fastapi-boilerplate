from uuid import uuid4


async def test_books_require_auth(client):
    # No auth override on the plain `client` → the guard rejects the request.
    resp = await client.get("/api/v1/books")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "http_error"


async def test_list_books_empty_page(auth_client):
    resp = await auth_client.get("/api/v1/books")
    assert resp.status_code == 200
    assert resp.json() == {"items": [], "total": 0, "limit": 20, "offset": 0}


async def test_create_then_fetch_book(auth_client):
    payload = {"title": "Clean   Code", "author": "Robert Martin", "year": 2008, "price": 30.5}
    created = await auth_client.post("/api/v1/books", json=payload)
    assert created.status_code == 201
    body = created.json()
    assert body["title"] == "Clean Code"          # inner whitespace collapsed by validator

    fetched = await auth_client.get(f"/api/v1/books/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["author"] == "Robert Martin"


async def test_filter_and_paginate(auth_client):
    for i in range(3):
        await auth_client.post(
            "/api/v1/books",
            json={"title": f"Book {i}", "author": "Ada Lovelace", "year": 2000 + i, "price": 10},
        )
    await auth_client.post(
        "/api/v1/books",
        json={"title": "Other", "author": "Someone Else", "year": 1999, "price": 5},
    )

    resp = await auth_client.get("/api/v1/books", params={"author": "lovelace", "limit": 2})
    body = resp.json()
    assert body["total"] == 3          # 3 match the filter
    assert len(body["items"]) == 2     # but only 2 on this page
    assert body["limit"] == 2


async def test_book_not_found_uses_error_schema(auth_client):
    resp = await auth_client.get(f"/api/v1/books/{uuid4()}")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


async def test_validation_error_shape(auth_client):
    resp = await auth_client.post("/api/v1/books", json={"title": "", "author": "A", "year": 5, "price": -1})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


async def test_request_id_header_present(auth_client):
    resp = await auth_client.get("/api/v1/books")
    assert "x-request-id" in resp.headers
    assert "x-process-time-ms" in resp.headers
