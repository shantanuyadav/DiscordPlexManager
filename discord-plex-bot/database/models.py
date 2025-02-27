# Data models for handling subscriptions and Plex servers
from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional

@dataclass
class Subscription:
    id: str
    plex_username: str
    discord_username: Optional[str]
    email: Optional[str]
    server_name: str
    duration: str
    payment_method: str
    payment_id: str
    start_date: date
    end_date: Optional[date]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data.get('id'),
            plex_username=data.get('plex_username'),
            discord_username=data.get('discord_username'),
            email=data.get('email'),
            server_name=data.get('server_name'),
            duration=data.get('duration'),
            payment_method=data.get('payment_method'),
            payment_id=data.get('payment_id'),
            start_date=datetime.strptime(data.get('start_date'), '%Y-%m-%d').date(),
            end_date=datetime.strptime(data.get('end_date'), '%Y-%m-%d').date() if data.get('end_date') else None,
            created_at=datetime.fromisoformat(data.get('created_at')) if data.get('created_at') else None,
            updated_at=datetime.fromisoformat(data.get('updated_at')) if data.get('updated_at') else None
        )

@dataclass
class PlexServer:
    id: str
    server_name: str
    plex_url: str
    plex_token: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data.get('id'),
            server_name=data.get('server_name'),
            plex_url=data.get('plex_url'),
            plex_token=data.get('plex_token'),
            created_at=datetime.fromisoformat(data.get('created_at')) if data.get('created_at') else None,
            updated_at=datetime.fromisoformat(data.get('updated_at')) if data.get('updated_at') else None
        )