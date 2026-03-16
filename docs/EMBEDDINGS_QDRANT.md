# Embedding text and images with Google GenAI and storing in Qdrant

This project uses **Google GenAI** (Gemini) for embeddings and **Qdrant** for vector storage. Data lives in **PostgreSQL** (source of truth); Qdrant is used for **indexing** and semantic search.

## Config

- **GEMINI_API_KEY**: Google AI API key (used by `embed_text` and `embed_image`).
- **QDRANT_URL**: Qdrant server URL (e.g. `http://localhost:6333`).
- **QDRANT_API_KEY**: Optional API key for Qdrant Cloud.

## Shared modules

- **`app/shared/embeddings.py`**: `embed_text()`, `embed_image()` using `google.genai`.
- **`app/shared/qdrant_client.py`**: `get_qdrant_client()`, `ensure_collection()`, `upsert_points()`, `delete_points_by_ids()`.

## How to use `embed_text`

```python
from app.shared.embeddings import embed_text

# One or more strings
vectors = embed_text("Lao restaurant with riverside seating")
# vectors: list of list[float], one per input string

# For indexing documents (e.g. restaurant descriptions)
doc_vectors = embed_text(
    ["First paragraph...", "Second paragraph..."],
    task_type="RETRIEVAL_DOCUMENT",
    output_dimensionality=768,
)

# For search queries
query_vector = embed_text(
    "riverside Lao food",
    task_type="RETRIEVAL_QUERY",
    output_dimensionality=768,
)[0]
```

## How to use `embed_image`

```python
from app.shared.embeddings import embed_image

with open("cover.jpg", "rb") as f:
    image_bytes = f.read()

vector = embed_image(
    image_bytes,
    mime_type="image/jpeg",
    output_dimensionality=768,
)
# vector: list[float], same dimension as text for shared collections
```

Note: The Gemini embedding model is text-only. If the API does not accept image input, `embed_image` falls back to a **deterministic pseudo-embedding** from image bytes (same image → same vector) so you can still store and index in Qdrant.

## Storing in Qdrant

```python
from qdrant_client.models import Distance, VectorParams, PointStruct
from app.shared.qdrant_client import get_qdrant_client, ensure_collection, upsert_points
from app.shared.embeddings import embed_text, EMBED_OUTPUT_DIM

# 1. Ensure collection exists (768 matches embed_text default)
ensure_collection("restaurants", vector_size=EMBED_OUTPUT_DIM, distance=Distance.COSINE)

# 2. Embed and upsert
text = "Lan Xang Kitchen – Lao dishes, riverside."
vectors = embed_text(text, task_type="RETRIEVAL_DOCUMENT", output_dimensionality=EMBED_OUTPUT_DIM)
point = PointStruct(
    id="rest_001",
    vector=vectors[0],
    payload={"restaurant_id": "rest_001", "name": "Lan Xang Kitchen", "slug": "lan-xang-kitchen"},
)
upsert_points("restaurants", [point])

# 3. Search (e.g. in a service)
from app.shared.qdrant_client import get_qdrant_client
from app.shared.embeddings import embed_text

client = get_qdrant_client()
query_vec = embed_text("riverside Lao food", task_type="RETRIEVAL_QUERY", output_dimensionality=768)[0]
hits = client.search(collection_name="restaurants", query_vector=query_vec, limit=10, with_payload=True)
# Then load full records from PostgreSQL by hit.payload["restaurant_id"]
```

## Restaurants API and indexing

- **POST /api/v1/restaurants**: Body is FormData with `data` (JSON string, e.g. from `restaurant.json`). Optional files: `cover_image_file`, `menu_source_file`, `gallery_0`, `gallery_1`, ...  
  On create, the app builds searchable text (name, description, tags, menu items, etc.), calls `embed_text`, and upserts one point per restaurant into the `restaurants` collection. Optionally it also embeds the cover image with `embed_image` and stores a second point (`restaurant_id_cover`).
- **GET /api/v1/restaurants/search?q=...**: Embeds the query with `RETRIEVAL_QUERY`, searches Qdrant, then returns full restaurant records from PostgreSQL.
- **PUT /api/v1/restaurants/{id}**: Can update and re-index (same text embedding flow).
- **DELETE /api/v1/restaurants/{id}**: Deletes from PostgreSQL and removes the corresponding points from Qdrant.

All of this uses **indexing**: PostgreSQL holds the canonical data; Qdrant holds vectors for fast semantic search.
