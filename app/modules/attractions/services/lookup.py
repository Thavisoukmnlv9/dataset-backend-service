"""Service for attraction lookup functionality (dropdowns, selectors)."""
from typing import Dict, Any

from fastapi import HTTPException, status

from app.prisma import prisma
from app.modules.attractions.schemas.attraction import AttractionLookupItem, AttractionLookupQueryDTO


async def lookup_attractions(query: AttractionLookupQueryDTO) -> Dict[str, Any]:
    """Lookup attractions with search and pagination."""
    try:
        where_clause: Dict[str, Any] = {}
        if query.q:
            where_clause["OR"] = [
                {"name": {"contains": query.q, "mode": "insensitive"}},
                {"slug": {"contains": query.q, "mode": "insensitive"}},
            ]

        attractions = await prisma.attraction.find_many(
            where=where_clause,
            order={"name": "asc"},
            skip=query.skip,
            take=query.limit,
        )

        total_count = await prisma.attraction.count(where=where_clause)

        items = [
            AttractionLookupItem(id=a.id, name=a.name or a.slug or a.id)
            for a in attractions
        ]

        return {
            "success": True,
            "data": {
                "items": [item.model_dump() for item in items],
                "total": total_count,
            },
            "message": "Attractions lookup successful",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error looking up attractions: {str(e)}",
        )


async def lookup_attraction_by_id(attraction_id: str) -> Dict[str, Any]:
    """Lookup a specific attraction by ID."""
    try:
        attraction = await prisma.attraction.find_unique(
            where={"id": attraction_id},
        )

        if not attraction:
            return {"success": True, "data": {"item": None}, "message": "Attraction not found"}

        item = AttractionLookupItem(
            id=attraction.id,
            name=attraction.name or attraction.slug or attraction.id,
        )

        return {
            "success": True,
            "data": {"item": item.model_dump()},
            "message": "Attraction found successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error looking up attraction: {str(e)}",
        )
