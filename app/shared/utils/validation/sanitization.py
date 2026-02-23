"""
Input sanitization utilities to prevent XSS and injection attacks.
"""
import re
import html
from typing import Any
from html.parser import HTMLParser
import logging

logger = logging.getLogger(__name__)


def sanitize_string(value: str, max_length: int = 10000) -> str:
    """
    Sanitize a string by:
    1. HTML entity encoding to prevent XSS
    2. Stripping potentially dangerous characters
    3. Limiting length
    
    Args:
        value: The string to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
    """
    if not isinstance(value, str):
        return value
    
    # Truncate if too long
    if len(value) > max_length:
        logger.warning(f"String truncated from {len(value)} to {max_length} characters")
        value = value[:max_length]
    
    # HTML escape to prevent XSS
    sanitized = html.escape(value)
    
    # Remove any remaining suspicious patterns
    # Remove potential SQL injection patterns
    suspicious_patterns = [
        (r";\s*--", ""),  # SQL comment
        (r";\s*/\*", ""),  # SQL block comment start
        (r"\*/\s*;", ""),  # SQL block comment end
        (r"union\s+select", "UNION SELECT"),  # Case-insensitive union
        (r"drop\s+table", "DROP TABLE"),  # Drop table
        (r"delete\s+from", "DELETE FROM"),  # Delete from
        (r"<script", "&lt;script"),  # Script tags
        (r"javascript:", ""),  # JavaScript protocol
        (r"on\w+\s*=", ""),  # Event handlers like onClick=
    ]
    
    for pattern, replacement in suspicious_patterns:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
    
    return sanitized


def sanitize_html(value: str, allowed_tags: list = None) -> str:
    """
    Sanitize HTML content by removing dangerous tags and attributes.
    
    Args:
        value: HTML string to sanitize
        allowed_tags: List of allowed HTML tags (default: safe tags only)
        
    Returns:
        Sanitized HTML string
    """
    if not isinstance(value, str):
        return value
    
    if allowed_tags is None:
        # Whitelist of safe HTML tags
        allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']
    
    # This is a basic implementation - in production, use a library like `bleach`
    # For now, we'll just HTML escape everything
    sanitized = html.escape(value)
    
    return sanitized


def sanitize_sql_injection(value: str) -> str:
    """
    Basic SQL injection prevention by escaping quotes and removing dangerous patterns.
    
    Args:
        value: String that will be used in SQL query
        
    Returns:
        Sanitized string safe for SQL queries
    """
    if not isinstance(value, str):
        return value
    
    # Escape single quotes
    sanitized = value.replace("'", "''")
    
    # Remove dangerous SQL patterns
    dangerous_patterns = [
        r";\s*--",  # SQL comment
        r";\s*/\*",  # SQL block comment start
        r"\bexec\b",  # SQL exec
        r"\bsp_executesql\b",  # SQL Server exec
    ]
    
    for pattern in dangerous_patterns:
        sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE)
    
    return sanitized


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent directory traversal and other attacks.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename safe for filesystem operations
    """
    if not isinstance(filename, str):
        return filename
    
    # Remove directory traversal attempts
    sanitized = filename.replace('..', '')
    sanitized = sanitized.replace('/', '_')
    sanitized = sanitized.replace('\\', '_')
    
    # Remove null bytes
    sanitized = sanitized.replace('\x00', '')
    
    # Remove control characters
    sanitized = re.sub(r'[\x00-\x1f\x7f]', '', sanitized)
    
    # Limit length
    if len(sanitized) > 255:
        sanitized = sanitized[:255]
    
    return sanitized


def sanitize_url(url: str) -> str:
    """
    Sanitize URL to prevent dangerous protocols and injections.
    
    Args:
        url: URL string
        
    Returns:
        Sanitized URL
    """
    if not isinstance(url, str):
        return url
    
    # Only allow http, https, mailto protocols
    allowed_protocols = ['http', 'https', 'mailto']
    
    url_lower = url.lower()
    for protocol in allowed_protocols:
        if url_lower.startswith(f'{protocol}://') or url_lower.startswith(f'{protocol}:'):
            return url
    
    # If no allowed protocol, treat as dangerous
    logger.warning(f"Dangerous URL protocol detected: {url}")
    return ""


def sanitize_dict(data: dict, sanitize_recursive: bool = True) -> dict:
    """
    Recursively sanitize a dictionary.
    
    Args:
        data: Dictionary to sanitize
        sanitize_recursive: Whether to sanitize nested dicts and lists
        
    Returns:
        Sanitized dictionary
    """
    if not isinstance(data, dict):
        return data
    
    sanitized = {}
    for key, value in data.items():
        # Sanitize key
        safe_key = sanitize_string(str(key))
        
        # Sanitize value based on type
        if isinstance(value, str):
            safe_value = sanitize_string(value)
        elif isinstance(value, dict) and sanitize_recursive:
            safe_value = sanitize_dict(value, sanitize_recursive)
        elif isinstance(value, list) and sanitize_recursive:
            safe_value = [sanitize_dict(item, sanitize_recursive) if isinstance(item, dict) else 
                         (sanitize_string(item) if isinstance(item, str) else item) 
                         for item in value]
        else:
            safe_value = value
        
        sanitized[safe_key] = safe_value
    
    return sanitized


class SanitizationError(Exception):
    """Raised when sanitization fails or detects malicious content."""
    pass

