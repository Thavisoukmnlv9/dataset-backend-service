"""
CLI display utilities for startup banner and logging.
Handles terminal colors, ASCII art, and formatted output.
"""

# Service icons
SERVICE_ICONS = {
    "api": "🌐",
    "docs": "📚",
    "database": "🗄️",
    "database_url": "🔗",
    "pgadmin": "🗄️",
    "storage": "💾",
    "cache": "⚡",
    "monitoring": "📊",
    "redisinsight": "🔍"
}

# Terminal colors
COLORS = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m"
}

# ASCII art
ASCII_ART = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║    ████████╗██████╗ ██╗██████╗ ██████╗ ██╗   ██╗██████╗ ██╗   ██╗
║    ╚══██╔══╝██╔══██╗██║██╔══██╗██╔══██╗██║   ██║██╔══██╗╚██╗ ██╔╝
║       ██║   ██████╔╝██║██████╔╝██████╔╝██║   ██║██║  ██║ ╚████╔╝ 
║       ██║   ██╔══██╗██║██╔══██╗██╔══██╗██║   ██║██║  ██║  ╚██╔╝  
║       ██║   ██║  ██║██║██████╔╝██║  ██║╚██████╔╝██████╔╝   ██║   
║       ╚═╝   ╚═╝  ╚═╝╚═╝╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═════╝    ╚═╝   
║                                                              ║
║                    Tourism Middleware API                     ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""

# Service status
SERVICE_STATUS = {
    "healthy": "✅",
    "warning": "⚠️",
    "error": "❌",
    "loading": "🔄"
}

