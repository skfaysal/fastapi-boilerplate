def _user(**overrides):
    base = {
        "username": "Alice",
        "email": "Alice@Example.com",
        "first_name": "Al",
        "last_name": "Ice",
        "password": "supersecret123",
    }
    return {**base, **overrides}


async def test_register_normalizes_and_hides_hash(client):
    resp = await client.post("/api/v1/auth/register", json=_user())
    assert resp.status_code == 201
    body = resp.json()
    assert body["username"] == "alice"            # lowercased by field_validator
    assert body["email"] == "alice@example.com"
    assert "hashed_password" not in body          # UserRead never exposes it


async def test_register_then_login(client):
    await client.post("/api/v1/auth/register", json=_user())
    # OAuth2 password form: username field carries the email.
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "alice@example.com", "password": "supersecret123"},
    )
    assert resp.status_code == 200
    tokens = resp.json()
    assert tokens["access_token"] and tokens["refresh_token"]
    assert tokens["token_type"] == "bearer"


async def test_duplicate_email_conflicts(client):
    assert (await client.post("/api/v1/auth/register", json=_user())).status_code == 201
    resp = await client.post("/api/v1/auth/register", json=_user(username="alice2"))
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "conflict"


async def test_password_cannot_contain_username(client):
    resp = await client.post("/api/v1/auth/register", json=_user(username="charlie", password="charlie-pass-1"))
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


async def test_wrong_password_is_401(client):
    await client.post("/api/v1/auth/register", json=_user())
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "alice@example.com", "password": "wrong-password"},
    )
    assert resp.status_code == 401
