from __future__ import annotations

from typing import List, Optional, Dict, Any, Union

from .http import HTTPClient, Route


class DiscordObject:
    def __init__(self, data):
        self._data = data
        self.id = data['id']

    def __eq__(self, other) -> bool:
        return other.id == self.id

    def __ne__(self, other) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return self.id >> 22

    def json(self):
        """Returns the original JSON data for this model."""
        return self._data


class TokenResponse(DiscordObject):
    def __init__(self, *, data: dict) -> None:
        self._data = data
        self.access_token: str = self._data["access_token"]
        self.token_type: str = self._data["token_type"]
        self.expires_in: int = self._data["expires_in"]
        self.refresh_token: str = self._data["refresh_token"]
        self.scope: str = self._data["scope"]


class Guild(DiscordObject):
    def __init__(self, *, data: dict, user: User) -> None:
        self._data = data

        self._icon_hash = self._data.get("icon")
        self._icon_format = None if not self._icon_hash else "gif" if self._icon_hash.startswith("a") else "png"

        self.user = user

        self.id: int = self._data["id", 0]
        self.name: str = self._data["name"]
        self.icon_url: Optional[str] = "https://cdn.discordapp.com/icons/{0.id}/{0._icon_hash}.{0._icon_format}".format(self) if self._icon_format else None
        self.is_user_owner: Optional[bool] = self._data.get("owner")
        self.features: List[str] = self._data.get("features", [])


class User(DiscordObject):
    def __init__(self, *, http: HTTPClient, data: dict, acr: Union[Dict[str, Any], TokenResponse]):
        self._data = data
        self._http = http
        if isinstance(acr, TokenResponse):
            self._acr: TokenResponse = acr
        else:
            self._acr: TokenResponse = TokenResponse(data=acr)

        self._avatar_hash = self._data["avatar"]
        self._avatar_format = None if not self._avatar_hash else "gif" if self._avatar_hash.startswith("a") else "png"

        self.id: int = self._data["id"]
        self.name: Optional[str] = self._data["username"]
        self.avatar_url: Optional[str] = None if not self._avatar_hash else "https://cdn.discordapp.com/avatars/{0.id}/{0._avatar_hash}.{0._avatar_format}".format(
            self
        )
        self.discriminator: int = self._data["discriminator"]
        self.mfa_enabled: Optional[bool] = self._data.get("mfa_enabled")
        self.email: Optional[str] = self._data.get("email")
        self.verified: Optional[bool] = self._data.get("verified")

        self.guilds: List[Guild] = []  # this is filled in when fetch_guilds is called

    @property
    def access_token(self) -> Optional[str]:
        return self._acr.access_token

    @property
    def refresh_token(self) -> str:
        return self._acr.refresh_token

    def __str__(self) -> str:
        return "{0.name}#{0.discriminator}".format(self)

    def __repr__(self) -> str:
        return "<User id={0.id} name={0.name} discriminator={0.discriminator} verified={0.verified}>".format(
            self
        )

    async def refresh(self) -> TokenResponse:
        """Refreshes the access token for the user and returns a fresh access token response.

        :return: A class holding information about the new access token
        :rtype: AccessTokenResponse
        """
        refresh_token = self.refresh_token
        route = Route("POST", "/oauth2/token")
        post_data = {
            "client_id": self._http._state_info["client_id"],
            "client_secret": self._http._state_info["client_secret"],
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        request_data = await self._http.request(route, data=post_data)
        token_resp = TokenResponse(data=request_data)
        self._acr = token_resp
        return token_resp

    async def fetch_guilds(self, *, refresh: bool = True) -> List[Guild]:
        """Makes an api call to fetch the guilds the user is in. Can fill a normal dictionary cache.

        :param refresh: Whether or not to refresh the guild cache attached to this user object. If false, returns the cached guilds, defaults to True
        :type refresh: bool, optional
        :return: A List of Guild objects either from cache or returned from the api call
        :rtype: List[Guild]
        """
        if not refresh and self.guilds:
            return self.guilds

        route = Route("GET", "/users/@me/guilds")
        headers = {"Authorization": "Bearer {}".format(self.access_token)}
        resp = await self._http.request(route, headers=headers)
        self.guilds = []
        for array in resp:
            guild = Guild(data=array, user=self)
            self.guilds.append(guild)

        return self.guilds
