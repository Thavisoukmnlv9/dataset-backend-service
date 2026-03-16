"""
Prisma database client module for kanom Tourism Middleware.

This module provides the Prisma client instance for database operations.
"""

from .client import prisma, db, connect_db, disconnect_db, cleanup_all_connections, ensure_connection

__all__ = ["prisma", "db", "connect_db", "disconnect_db", "cleanup_all_connections", "ensure_connection"]
