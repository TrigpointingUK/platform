"""
Schemas for the connected applications (Auth0 user grants) endpoints.
"""

from typing import List, Optional

from pydantic import BaseModel


class ConnectedApp(BaseModel):
    """An application the user has authorised to access their account."""

    grant_id: str
    client_id: str
    client_name: Optional[str] = None
    audience: Optional[str] = None
    scopes: List[str] = []


class ConnectedAppsResponse(BaseModel):
    """List of applications the user has authorised."""

    apps: List[ConnectedApp]
