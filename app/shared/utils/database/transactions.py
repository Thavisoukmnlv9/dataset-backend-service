"""
Transaction management utilities for database operations.
"""
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict
from app.prisma import prisma

logger = logging.getLogger(__name__)


@asynccontextmanager
async def database_transaction():
    """
    Context manager for database transactions.
    
    Usage:
        async with database_transaction() as tx:
            user = await tx.user.create(...)
            profile = await tx.profile.create(...)
    
    If any exception occurs, all changes are rolled back.
    """
    try:
        async with prisma.tx() as transaction:
            logger.debug("Transaction started")
            yield transaction
            logger.debug("Transaction committed successfully")
    except Exception as e:
        logger.error(f"Transaction failed, rolling back: {e}", exc_info=True)
        raise


async def execute_with_transaction(func, *args, **kwargs):
    """
    Execute a function within a database transaction.
    
    Args:
        func: Async function to execute
        *args: Positional arguments for func
        **kwargs: Keyword arguments for func
        
    Returns:
        Result of func execution
        
    Raises:
        Exception: If transaction fails
    """
    try:
        async with prisma.tx() as transaction:
            # Replace prisma with transaction in kwargs
            if 'db' in kwargs:
                kwargs['db'] = transaction
            elif 'transaction' in kwargs:
                kwargs['transaction'] = transaction
            
            result = await func(*args, **kwargs)
            return result
            
    except Exception as e:
        logger.error(f"Transaction execution failed: {e}", exc_info=True)
        raise


class TransactionManager:
    """
    Manager class for handling transactions across multiple operations.
    """
    
    def __init__(self):
        self.transaction = None
    
    async def begin(self):
        """Start a new transaction"""
        self.transaction = await prisma.tx().__aenter__()
        logger.debug("TransactionManager: Transaction started")
    
    async def commit(self):
        """Commit the transaction"""
        if self.transaction:
            await self.transaction.__aexit__(None, None, None)
            logger.debug("TransactionManager: Transaction committed")
            self.transaction = None
    
    async def rollback(self):
        """Rollback the transaction"""
        if self.transaction:
            await self.transaction.__aexit__(Exception("Rollback"), None, None)
            logger.debug("TransactionManager: Transaction rolled back")
            self.transaction = None
    
    async def __aenter__(self):
        await self.begin()
        return self.transaction
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await self.rollback()
        else:
            await self.commit()


async def atomic_operation(operations: list):
    """
    Execute multiple operations atomically.
    
    Args:
        operations: List of tuples (function, *args, **kwargs)
        
    Example:
        await atomic_operation([
            (create_user, user_data),
            (create_profile, profile_data),
            (update_user, user_id, update_data),
        ])
    """
    try:
        async with prisma.tx() as transaction:
            results = []
            
            for operation in operations:
                if len(operation) == 2:
                    func, args = operation
                    kwargs = {}
                elif len(operation) == 3:
                    func, args, kwargs = operation
                else:
                    raise ValueError("Invalid operation tuple")
                
                # Execute with transaction context
                result = await func(*args, transaction=transaction, **kwargs)
                results.append(result)
            
            return results
            
    except Exception as e:
        logger.error(f"Atomic operation failed: {e}", exc_info=True)
        raise

