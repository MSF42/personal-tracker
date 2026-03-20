import pytest


@pytest.mark.asyncio
async def test_upload_image_rejects_mismatched_magic_bytes(client):
    """A file claiming to be JPEG but with wrong magic bytes must be rejected."""
    fake_jpeg = b"This is not a JPEG" + b"\x00" * 50
    response = await client.post(
        "/api/v1/notes/images",
        files={"file": ("photo.jpg", fake_jpeg, "image/jpeg")},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_upload_image_accepts_valid_jpeg(client):
    """A real JPEG magic header must be accepted."""
    valid_jpeg = b"\xff\xd8\xff\xe0" + b"\x00" * 100
    response = await client.post(
        "/api/v1/notes/images",
        files={"file": ("photo.jpg", valid_jpeg, "image/jpeg")},
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_upload_image_accepts_valid_png(client):
    """A real PNG magic header must be accepted."""
    valid_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    response = await client.post(
        "/api/v1/notes/images",
        files={"file": ("photo.png", valid_png, "image/png")},
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_upload_image_rejects_mismatched_png(client):
    """A file claiming to be PNG but with wrong magic bytes must be rejected."""
    fake_png = b"fake data here" + b"\x00" * 50
    response = await client.post(
        "/api/v1/notes/images",
        files={"file": ("photo.png", fake_png, "image/png")},
    )
    assert response.status_code == 422
