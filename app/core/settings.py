"""
Application settings and configuration.
"""
import logging
from typing import Dict
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AppSettings(BaseModel):
    """Application-specific settings"""
    title: str = "kanom Tourism Middleware API"
    description: str = "Comprehensive API for kanom tourism platform with modular architecture."
    version: str = "2.1.0"
    contact: Dict[str, str] = {
        "name": "Bounyalith Chanrasanichone",
        "email": "bounyalith.c@gmail.com",
    }
    license_info: Dict[str, str] = {
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    }


class ServiceConfig(BaseModel):
    """Service configuration for loading routes"""
    name: str
    import_path: str
    router_name: str = "router"
    enabled: bool = True


SERVICES_TO_LOAD = [
    ServiceConfig(name="Auth", import_path="app.modules.auth.api.routes", router_name="router"),
    ServiceConfig(name="Users", import_path="app.modules.users.api.routes", router_name="router"),
    ServiceConfig(name="Restaurants", import_path="app.modules.restaurants.api.routes", router_name="router"),
    ServiceConfig(name="Cafes", import_path="app.modules.cafes.api.routes", router_name="router"),
    ServiceConfig(name="Bars", import_path="app.modules.bars.api.routes", router_name="router"),
    ServiceConfig(name="Attractions", import_path="app.modules.attractions.api.routes", router_name="router"),
    ServiceConfig(name="Souvenirs", import_path="app.modules.souvenirs.api.routes", router_name="router"),
]

API_ENDPOINTS = {
    "auth": "/api/v1/auth",
    "users": "/api/v1/users",
    "restaurants": "/api/v1/restaurants",
    "cafes": "/api/v1/cafes",
    "bars": "/api/v1/bars",
    "attractions": "/api/v1/attractions",
    "souvenirs": "/api/v1/souvenirs",
}

app_settings = AppSettings()
