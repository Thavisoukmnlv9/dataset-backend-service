"""
Integration tests: connect to Qdrant and verify restaurants collection data.

Run with Qdrant available (e.g. QDRANT_URL=http://localhost:6333):
  pytest tests/test_restaurants_qdrant.py -v

Skip if Qdrant is not running:
  pytest tests/test_restaurants_qdrant.py -v (will skip on connection error)
"""

import logging
from typing import Any, Dict, List, Set

import pytest

logger = logging.getLogger(__name__)

# Collection name must match create.py
QDRANT_COLLECTION = "restaurants"

# Required top-level payload keys (after sync/create)
REQUIRED_PAYLOAD_KEYS = {"id", "name", "slug", "type", "category", "status"}

# Tags are stored as list of strings (tag value only)


def get_qdrant_client_optional():
    """Return Qdrant client or None if connection fails (e.g. Qdrant not running)."""
    try:
        from app.shared.qdrant_client import get_qdrant_client
        return get_qdrant_client()
    except Exception as e:
        logger.warning("Qdrant client not available: %s", e)
        return None


def test_text_point_payload_structure(restaurants_points):
    """Points with type='text' must have tags as list of strings, gallery as list of dicts."""
    errors = []
    for p in restaurants_points:
        payload = p.payload or {}
        if payload.get("type") != "text":
            continue
        # tags: list of strings (tag values)
        tags = payload.get("tags")
        if tags is not None:
            if not isinstance(tags, list):
                errors.append("%s: tags is not a list" % p.id)
            else:
                for i, t in enumerate(tags):
                    if not isinstance(t, str):
                        errors.append("%s: tags[%d] should be string, got: %s" % (p.id, i, type(t).__name__))
        # gallery: list of dicts (after url drop, at least description may be present)
        gallery = payload.get("gallery")
        if gallery is not None:
            if not isinstance(gallery, list):
                errors.append("%s: gallery is not a list" % p.id)
            else:
                for i, g in enumerate(gallery):
                    if not isinstance(g, dict):
                        errors.append("%s: gallery[%d] is not a dict" % (p.id, i))
    assert not errors, "Payload structure errors: %s" % errors[:10]
    logger.info("Text point payload structure OK (tags/gallery validated)")


def fetch_all_points(client) -> List[Dict[str, Any]]:
    """Scroll and return all points in the collection."""
    points = []
    offset = None
    while True:
        result, next_offset = client.scroll(
            collection_name=QDRANT_COLLECTION,
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        points.extend(result)
        if next_offset is None:
            break
        offset = next_offset
    return points


@pytest.fixture(scope="module")
def qdrant_client():
    """Qdrant client; skip all tests in module if unavailable."""
    client = get_qdrant_client_optional()
    if client is None:
        pytest.skip("Qdrant not available (set QDRANT_URL or start Qdrant)")
    return client


@pytest.fixture(scope="module")
def restaurants_points(qdrant_client):
    """All points in the restaurants collection."""
    try:
        return fetch_all_points(qdrant_client)
    except Exception as e:
        pytest.skip("Could not fetch points from Qdrant: %s" % e)


def test_qdrant_connection(qdrant_client):
    """Verify we can connect to Qdrant and the restaurants collection exists."""
    info = qdrant_client.get_collection(QDRANT_COLLECTION)
    assert info is not None
    assert getattr(info, "points_count", 0) is not None
    assert getattr(info, "status", None) is not None
    logger.info("Collection %s: points count=%s", QDRANT_COLLECTION, getattr(info, "points_count", "?"))


def test_no_duplicate_point_ids(restaurants_points):
    """Each point ID must appear only once (no duplicate upserts)."""
    seen_ids: Set[str] = set()
    for p in restaurants_points:
        pid = str(p.id)
        assert pid not in seen_ids, "Duplicate point id in Qdrant: %s" % pid
        seen_ids.add(pid)
    logger.info("No duplicate point IDs; total points=%d", len(seen_ids))


def test_only_text_points_no_image(restaurants_points):
    """Only type 'text' points are stored; no type 'image' (cover) points."""
    for p in restaurants_points:
        payload = p.payload or {}
        point_type = payload.get("type")
        assert point_type == "text", "Expected only type 'text' in Qdrant, got type=%s (point id=%s)" % (point_type, p.id)
    logger.info("All points have type 'text' (no image points)")


def test_each_restaurant_id_at_most_one_text_point(restaurants_points):
    """For each restaurant id (payload.id), there should be at most one point with type='text'."""
    text_by_restaurant: Dict[str, List[str]] = {}  # restaurant_id -> list of point ids
    for p in restaurants_points:
        payload = p.payload or {}
        point_type = payload.get("type")
        rest_id = payload.get("id")
        if not rest_id:
            continue
        rest_id = str(rest_id)
        if point_type == "text":
            text_by_restaurant.setdefault(rest_id, []).append(str(p.id))

    duplicates = {rid: point_ids for rid, point_ids in text_by_restaurant.items() if len(point_ids) > 1}
    assert not duplicates, "Restaurant(s) have more than one text point in Qdrant: %s" % duplicates
    logger.info("Each restaurant has at most one text point; restaurants with text point=%d", len(text_by_restaurant))


def test_payload_has_required_keys(restaurants_points):
    """Each point payload must have required top-level keys."""
    missing = []
    for p in restaurants_points:
        payload = p.payload or {}
        for key in REQUIRED_PAYLOAD_KEYS:
            if key not in payload:
                missing.append((str(p.id), key))
    assert not missing, "Missing payload keys (point_id, key): %s" % missing


def test_payload_no_cover_image_url_or_url_in_nested(restaurants_points):
    """Payload must not contain cover_image_url, image_url, or url (they are stripped for Qdrant)."""
    forbidden = {"cover_image_url", "image_url", "url"}

    def check_obj(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in forbidden:
                    yield "%s has key %s" % (path or "payload", k)
                yield from check_obj(v, path or k)
        elif isinstance(obj, list):
            for i, x in enumerate(obj):
                yield from check_obj(x, "%s[%d]" % (path, i))

    errors = []
    for p in restaurants_points:
        for msg in check_obj(p.payload or {}):
            errors.append("%s: %s" % (p.id, msg))
    assert not errors, "Stripped keys still present: %s" % errors[:10]
