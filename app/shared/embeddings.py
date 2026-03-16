"""
Text and image embeddings using Google GenAI (Gemini), for indexing in Qdrant.

- embed_text: uses gemini-embedding-001 (RETRIEVAL_DOCUMENT / RETRIEVAL_QUERY).
- embed_image: uses same model with image part if supported; otherwise returns
  a deterministic pseudo-embedding from image bytes (same dimension as text)
  so you can store and index in Qdrant.
"""
import hashlib
import logging
from typing import List, Union

from app.core.config import settings
from google import genai
from google.genai import types
from google.genai.errors import ClientError

logger = logging.getLogger(__name__)

# Default embedding model and output size (Matryoshka; 768 is a good balance)
EMBED_MODEL = "models/gemini-embedding-001"
EMBED_OUTPUT_DIM = 768


def _get_genai_client() -> genai.Client:
    """Build GenAI client using app config."""
    api_key = getattr(settings, "gemini_api_key", None) or ""
    return genai.Client(api_key=api_key)


def embed_text(
    text: Union[str, List[str]],
    task_type: str = "RETRIEVAL_DOCUMENT",
    output_dimensionality: int = EMBED_OUTPUT_DIM,
) -> List[List[float]]:
    """
    Embed one or more texts using Google GenAI (gemini-embedding-001).

    Args:
        text: Single string or list of strings to embed.
        task_type: RETRIEVAL_DOCUMENT (for indexing) or RETRIEVAL_QUERY (for search).
        output_dimensionality: 128–3072; 768 or 1536 recommended.

    Returns:
        List of embedding vectors (list of float). One per input text.

    Raises:
        ClientError: From GenAI API (e.g. invalid key, quota).
    """
    if isinstance(text, str):
        text = [text]
    if not text:
        return []

    client = _get_genai_client()
    config = types.EmbedContentConfig(
        task_type=task_type,
        output_dimensionality=output_dimensionality,
    )
    result = client.models.embed_content(
        model=EMBED_MODEL,
        contents=text,
        config=config,
    )
    # result.embeddings: list of objects with .values
    out: List[List[float]] = []
    for emb in result.embeddings:
        out.append(list(emb.values))
    return out


def _pseudo_embed_from_bytes(data: bytes, dim: int) -> List[float]:
    """Deterministic pseudo-embedding of length dim from bytes (e.g. image)."""
    h = hashlib.sha256(data).digest()
    # Expand to dim floats in [-1, 1], then normalize to unit length
    floats: List[float] = []
    for i in range(dim):
        b = h[i % len(h)] if i < len(h) * 2 else h[(i // 2) % len(h)]
        floats.append((b / 127.5) - 1.0)
    # Normalize
    norm = (sum(x * x for x in floats)) ** 0.5
    if norm <= 0:
        return [1.0] + [0.0] * (dim - 1)
    return [x / norm for x in floats]


def embed_text_or_fallback(
    text: Union[str, List[str]],
    task_type: str = "RETRIEVAL_DOCUMENT",
    output_dimensionality: int = EMBED_OUTPUT_DIM,
) -> List[List[float]]:
    """
    Embed text with Gemini; if API fails or returns empty, use deterministic
    pseudo-embedding from text bytes so Qdrant always gets a vector (for RAG).
    """
    if isinstance(text, str):
        text = [text]
    if not text:
        return []

    try:
        vectors = embed_text(text, task_type=task_type, output_dimensionality=output_dimensionality)
        if vectors:
            return vectors
    except Exception as e:
        logger.warning("embed_text failed, using pseudo-embedding for Qdrant: %s", e)

    # Fallback: one pseudo-vector per input string
    out: List[List[float]] = []
    for t in text:
        raw = (t or "").encode("utf-8")
        if not raw:
            raw = b" "
        out.append(_pseudo_embed_from_bytes(raw, output_dimensionality))
    return out


def embed_image(
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
    output_dimensionality: int = EMBED_OUTPUT_DIM,
) -> List[float]:
    """
    Embed a single image for storage in Qdrant.

    Uses Google GenAI with inline image data when the embedding model supports it.
    If the API does not support image input (gemini-embedding-001 is text-only),
    falls back to a deterministic pseudo-embedding from image bytes so that:
    - Same image => same vector (dedup / consistency).
    - Vector dimension matches text embeddings for a shared collection.

    Args:
        image_bytes: Raw image bytes.
        mime_type: IANA type (e.g. image/jpeg, image/png).
        output_dimensionality: Must match your text embedding size (e.g. 768).

    Returns:
        Single embedding vector (list of float).
    """
    client = _get_genai_client()
    try:
        # Try GenAI embed with image part (may not be supported by embedding model)
        blob = types.Blob(mime_type=mime_type, data=image_bytes)
        part = types.Part(inline_data=blob)
        content = types.Content(parts=[part])
        config = types.EmbedContentConfig(
            output_dimensionality=output_dimensionality,
        )
        result = client.models.embed_content(
            model=EMBED_MODEL,
            contents=[content],
            config=config,
        )
        if result.embeddings and len(result.embeddings) > 0:
            return list(result.embeddings[0].values)
    except ClientError as e:
        logger.debug(
            "GenAI embed_content with image not supported or failed, using pseudo-embed: %s",
            e,
        )
    except Exception as e:
        logger.debug("embed_image fallback to pseudo-embed: %s", e)

    return _pseudo_embed_from_bytes(image_bytes, output_dimensionality)
