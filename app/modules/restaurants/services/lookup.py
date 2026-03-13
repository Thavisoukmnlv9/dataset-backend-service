"""Service for restaurant lookup functionality (dropdowns, selectors)."""
from typing import Dict, Any

from fastapi import HTTPException, status

from app.prisma import prisma
from app.modules.restaurants.schemas.restaurant import RestaurantLookupItem, RestaurantLookupQueryDTO


async def lookup_restaurants(query: RestaurantLookupQueryDTO) -> Dict[str, Any]:
    """Lookup restaurants with search and pagination."""
    try:
        where_clause: Dict[str, Any] = {}
        if query.q:
            where_clause["OR"] = [
                {"name": {"contains": query.q, "mode": "insensitive"}},
                {"slug": {"contains": query.q, "mode": "insensitive"}},
            ]

        restaurants = await prisma.restaurant.find_many(
            where=where_clause,
            order={"name": "asc"},
            skip=query.skip,
            take=query.limit,
        )

        total_count = await prisma.restaurant.count(where=where_clause)

        items = [
            RestaurantLookupItem(id=r.id, name=r.name or r.slug or r.id)
            for r in restaurants
        ]

        return {
            "success": True,
            "data": {
                "items": [item.model_dump() for item in items],
                "total": total_count,
            },
            "message": "Restaurants lookup successful",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error looking up restaurants: {str(e)}",
        )


async def lookup_restaurant_by_id(restaurant_id: str) -> Dict[str, Any]:
    """Lookup a specific restaurant by ID."""
    try:
        restaurant = await prisma.restaurant.find_unique(
            where={"id": restaurant_id},
        )

        if not restaurant:
            return {"success": True, "data": {"item": None}, "message": "Restaurant not found"}

        item = RestaurantLookupItem(
            id=restaurant.id,
            name=restaurant.name or restaurant.slug or restaurant.id,
        )

        return {
            "success": True,
            "data": {"item": item.model_dump()},
            "message": "Restaurant found successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error looking up restaurant: {str(e)}",
        )
