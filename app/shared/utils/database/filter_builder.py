"""Centralized filter builder to eliminate duplication across services"""

import json
import logging
from typing import Optional, Dict, Any, Type, TypeVar, List
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)
T = TypeVar('T')


class FilterBuilder:
    """Generic filter builder to reduce code duplication across 20+ service files"""
    
    @staticmethod
    def parse_frontend_filters(
        filters_json: Optional[str], 
        filter_class: Type[T]
    ) -> tuple[T, Optional[str]]:
        """
        Parse frontend filter JSON to Pydantic model.
        Handles common filter patterns.
        
        Args:
            filters_json: JSON string from frontend
            filter_class: Pydantic model class
            
        Returns:
            Tuple of (filters, search_query)
        
        Example:
            filters, search = FilterBuilder.parse_frontend_filters(
                '[{"field":"email","op":"contains","value":"test"}]',
                UserFilters
            )
        """
        if not filters_json:
            return filter_class(), None
        
        try:
            filters_data = json.loads(filters_json)
            if not isinstance(filters_data, list):
                return filter_class(), None
            
            # Build filter dict
            filter_dict = {}
            search_query = None
            
            for condition in filters_data:
                if not isinstance(condition, dict):
                    continue
                
                field = condition.get('field')
                op = condition.get('op')
                value = condition.get('value')
                
                if not field or not op:
                    continue
                
                # Handle different operations
                if field == 'search' and op == 'contains':
                    search_query = value
                elif op == 'contains':
                    filter_dict[field] = value
                elif op == 'eq':
                    filter_dict[field] = value
                elif op == 'gte':
                    filter_dict[f"{field}_from"] = value
                elif op == 'lte':
                    filter_dict[f"{field}_to"] = value
                elif op == 'in' and isinstance(value, list):
                    filter_dict[field] = value
            
            return filter_class(**filter_dict), search_query
            
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning(f"Failed to parse frontend filters: {e}")
            return filter_class(), None
    
    @staticmethod
    def parse_sort(sort_json: Optional[str]) -> Optional[Dict[str, str]]:
        """
        Parse frontend sort JSON.
        
        Example input: [{"field": "created_at", "dir": "desc"}]
        Example output: {"created_at": "desc"}
        
        Returns:
            Dict with field as key and direction as value
        """
        if not sort_json:
            return None
        
        try:
            sort_data = json.loads(sort_json)
            
            if isinstance(sort_data, list) and sort_data:
                item = sort_data[0]
                if isinstance(item, dict) and 'field' in item:
                    return {item['field']: item.get('dir', 'desc')}
            elif isinstance(sort_data, dict) and 'field' in sort_data:
                return {sort_data['field']: sort_data.get('dir', 'desc')}
        except (json.JSONDecodeError, TypeError, KeyError):
            pass
        
        return None
    
    @staticmethod
    def validate_pagination(page: int, limit: int, max_limit: int = 100):
        """
        Validate pagination parameters.
        
        Raises HTTPException if invalid.
        
        Args:
            page: Page number
            limit: Items per page
            max_limit: Maximum allowed items per page
        """
        if page < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Page must be greater than 0"
            )
        if limit < 1 or limit > max_limit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Limit must be between 1 and {max_limit}"
            )
    
    @staticmethod
    def build_search_conditions(
        search_query: str, 
        search_fields: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Build search conditions for text search across multiple fields.
        
        Args:
            search_query: Search text
            search_fields: Fields to search in
            
        Returns:
            List of OR conditions for Prisma
        """
        return [
            {field: {"contains": search_query, "mode": "insensitive"}}
            for field in search_fields
        ]
    
    @staticmethod
    def combine_with_search(
        base_where: Dict[str, Any],
        search_query: Optional[str],
        search_fields: List[str]
    ) -> Dict[str, Any]:
        """
        Combine base filters with search conditions.
        
        Args:
            base_where: Base where clause
            search_query: Optional search text
            search_fields: Fields to search
            
        Returns:
            Combined where clause with AND/OR logic
        """
        if not search_query:
            return base_where
        
        search_conditions = FilterBuilder.build_search_conditions(
            search_query, search_fields
        )
        
        if not base_where:
            return {"OR": search_conditions}
        
        return {
            "AND": [
                base_where,
                {"OR": search_conditions}
            ]
        }

