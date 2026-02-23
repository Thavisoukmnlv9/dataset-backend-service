"""
Startup display and server information utilities.
"""

import os
import socket
import platform
from typing import Dict, List, Optional
from .infrastructure_urls import get_infrastructure_urls, get_current_environment, get_service_url
from .cli_display import ASCII_ART, SERVICE_ICONS, COLORS

# Backward compatibility
SERVICE_URLS = get_infrastructure_urls()
API_INFO = {
    "name": "dataset Tourism Middleware",
    "version": "2.1.0",
    "description": "Comprehensive tourism management platform",
    "architecture": "Modular Monolith - Phase 1 Focus",
    "phase": "Phase 1 - Core Tourism Services"
}


def get_local_ip() -> Optional[str]:
    """Get the local network IP address (cross-platform)."""
    try:
        # Create a socket connection to determine local IP
        # Connect to a remote address (doesn't actually send data)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Connect to a non-routable address (doesn't actually connect)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            s.close()
            # Fallback: try to get hostname IP
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            if ip and ip != "127.0.0.1":
                return ip
    except Exception:
        pass
    
    # macOS/Linux fallback: try to get IP from network interfaces
    try:
        if platform.system() == "Darwin":  # macOS
            import subprocess
            result = subprocess.run(
                ["ipconfig", "getifaddr", "en0"],
                capture_output=True,
                text=True,
                timeout=1
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            # Try en1 as fallback
            result = subprocess.run(
                ["ipconfig", "getifaddr", "en1"],
                capture_output=True,
                text=True,
                timeout=1
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
    except Exception:
        pass
    
    return None


def get_port_from_url(url: str) -> str:
    """Extract port from URL, default to 8000 if not found."""
    try:
        if ":" in url.split("//")[-1]:
            port = url.split(":")[-1].split("/")[0]
            return port
    except Exception:
        pass
    return "8000"


class StartupDisplay:
    """Handles beautiful startup display and server information."""

    def __init__(self):
        self.colors = COLORS
        self.service_urls = SERVICE_URLS
        self.api_info = API_INFO

    def print_ascii_art(self) -> None:
        """Print the ASCII art logo."""
        print(self.colors["cyan"] + ASCII_ART + self.colors["reset"])

    def print_server_info(self) -> None:
        """Print server information."""
        print(
            f"{self.colors['bold']}{self.colors['green']}🚀 {self.api_info['name']} is running!{self.colors['reset']}")
        print(
            f"{self.colors['blue']}Version: {self.api_info['version']}{self.colors['reset']}")
        print(
            f"{self.colors['yellow']}Architecture: {self.api_info['architecture']}{self.colors['reset']}")
        print()

    def print_service_urls(self, custom_urls: Optional[Dict[str, str]] = None) -> None:
        """Print available service URLs."""
        urls = custom_urls or self.service_urls

        print(
            f"{self.colors['bold']}{self.colors['white']}📡 Available Services:{self.colors['reset']}")
        print(f"{self.colors['cyan']}{'─' * 60}{self.colors['reset']}")

        # Core API Services
        print(
            f"   {SERVICE_ICONS['api']} {self.colors['green']}API{self.colors['reset']}: {self.colors['blue']}{urls['api']}{self.colors['reset']}")
        
        # Network IP address for local network access
        local_ip = get_local_ip()
        if local_ip:
            port = get_port_from_url(urls['api'])
            network_url = f"http://{local_ip}:{port}"
            print(
                f"   📍 {self.colors['yellow']}Network{self.colors['reset']}: {self.colors['blue']}{network_url}{self.colors['reset']} {self.colors['cyan']}(local network - use this IP on other devices){self.colors['reset']}")
        
        print(
            f"   {SERVICE_ICONS['docs']} {self.colors['green']}API Documentation{self.colors['reset']}: {self.colors['blue']}{urls['docs']}{self.colors['reset']}")

        # Database & Storage
        print(f"   {SERVICE_ICONS['database']} {self.colors['green']}Database Management (pgAdmin){self.colors['reset']}: {self.colors['blue']}{urls['pgadmin']}{self.colors['reset']}")
        database_url = get_service_url('database')
        print(f"   {SERVICE_ICONS['database_url']} {self.colors['green']}Database URL{self.colors['reset']}: {self.colors['blue']}{database_url if database_url else 'Not configured'}{self.colors['reset']}")
        print(f"   {SERVICE_ICONS['storage']} {self.colors['green']}File Storage Console{self.colors['reset']}: {self.colors['blue']}{urls['file_storage']}{self.colors['reset']}")

        # Additional Services
        print(
            f"   {SERVICE_ICONS['cache']} {self.colors['green']}Redis Cache{self.colors['reset']}: {self.colors['blue']}{urls['redis']}{self.colors['reset']}")
        print(f"   {SERVICE_ICONS['redisinsight']} {self.colors['green']}RedisInsight{self.colors['reset']}: {self.colors['blue']}{urls['redisinsight']}{self.colors['reset']}")
        print(
            f"   {SERVICE_ICONS['storage']} {self.colors['green']}MinIO Storage{self.colors['reset']}: {self.colors['blue']}{urls['minio']}{self.colors['reset']}")

        print(f"{self.colors['cyan']}{'─' * 60}{self.colors['reset']}")

    def print_environment_info(self) -> None:
        """Print environment information."""
        env = get_current_environment()
        debug = os.getenv('DEBUG', 'false').lower() == 'true'

        print(
            f"{self.colors['bold']}{self.colors['white']}🔧 Environment:{self.colors['reset']}")
        print(
            f"   {self.colors['yellow']}Environment{self.colors['reset']}: {self.colors['blue']}{env.upper()}{self.colors['reset']}")
        print(
            f"   {self.colors['yellow']}Debug Mode{self.colors['reset']}: {self.colors['blue']}{'ON' if debug else 'OFF'}{self.colors['reset']}")
        print()

    def print_health_status(self, loaded_services: int, failed_services: int) -> None:
        """Print health status information."""
        total_services = loaded_services + failed_services
        success_rate = f"{loaded_services}/{total_services}" if total_services > 0 else "0/0"

        print(
            f"{self.colors['bold']}{self.colors['white']}💚 Health Status:{self.colors['reset']}")
        print(
            f"   {self.colors['green']}Loaded Services{self.colors['reset']}: {self.colors['blue']}{loaded_services}{self.colors['reset']}")
        print(
            f"   {self.colors['red']}Failed Services{self.colors['reset']}: {self.colors['blue']}{failed_services}{self.colors['reset']}")
        print(
            f"   {self.colors['yellow']}Success Rate{self.colors['reset']}: {self.colors['blue']}{success_rate}{self.colors['reset']}")
        print()

    def print_instructions(self) -> None:
        """Print usage instructions."""
        print(
            f"{self.colors['bold']}{self.colors['white']}📖 Quick Start:{self.colors['reset']}")
        print(
            f"   {self.colors['yellow']}•{self.colors['reset']} Visit {self.colors['blue']}{self.service_urls['docs']}{self.colors['reset']} for API documentation")
        print(f"   {self.colors['yellow']}•{self.colors['reset']} Check {self.colors['blue']}{self.service_urls['api']}/health{self.colors['reset']} for system status")
        print(
            f"   {self.colors['yellow']}•{self.colors['reset']} Use {self.colors['blue']}Ctrl+C{self.colors['reset']} to stop the server")
        print()

    def print_footer(self) -> None:
        """Print footer with separator."""
        print(f"{self.colors['cyan']}{'═' * 60}{self.colors['reset']}")
        print(
            f"{self.colors['bold']}{self.colors['green']}🎉 Server started successfully! Happy coding! 🎉{self.colors['reset']}")
        print(f"{self.colors['cyan']}{'═' * 60}{self.colors['reset']}\n")

    def display_full_startup(self, loaded_services: int = 0, failed_services: int = 0) -> None:
        """Display the complete startup information."""
        # Keep the service loading logs visible by NOT clearing the screen
        # Print all components
        self.print_ascii_art()
        self.print_server_info()
        self.print_service_urls()
        self.print_environment_info()
        self.print_health_status(loaded_services, failed_services)
        self.print_instructions()
        self.print_footer()

    def display_minimal_startup(self) -> None:
        """Display minimal startup information."""
        print(
            f"\n{self.colors['bold']}{self.colors['green']}🚀 {self.api_info['name']} is running!{self.colors['reset']}")
        print(f"{self.colors['cyan']}{'─' * 50}{self.colors['reset']}")
        print(
            f"   {SERVICE_ICONS['api']} API: {self.colors['blue']}{self.service_urls['api']}{self.colors['reset']}")
        print(
            f"   {SERVICE_ICONS['docs']} Docs: {self.colors['blue']}{self.service_urls['docs']}{self.colors['reset']}")
        print(
            f"   {SERVICE_ICONS['database']} pgAdmin: {self.colors['blue']}{self.service_urls['pgadmin']}{self.colors['reset']}")
        database_url = get_service_url('database')
        print(
            f"   {SERVICE_ICONS['database_url']} Database URL: {self.colors['blue']}{database_url if database_url else 'Not configured'}{self.colors['reset']}")
        print(
            f"   {SERVICE_ICONS['storage']} Storage: {self.colors['blue']}{self.service_urls['file_storage']}{self.colors['reset']}")
        print(
            f"   {SERVICE_ICONS['redisinsight']} RedisInsight: {self.colors['blue']}{self.service_urls['redisinsight']}{self.colors['reset']}")
        print(f"{self.colors['cyan']}{'─' * 50}{self.colors['reset']}")
        print(
            f"{self.colors['yellow']}Press Ctrl+C to stop the server{self.colors['reset']}\n")


# Create global instance
startup_display = StartupDisplay()
