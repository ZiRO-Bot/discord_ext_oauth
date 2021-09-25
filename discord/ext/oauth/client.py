from typing import Any, Dict, List, Optional, Union

from .http import HTTPClient, Route
from .models import User, TokenResponse

__all__: tuple = ("OAuth2Client",)


DISCORD_URL = "https://discord.com"
# API_URL = DISCORD_URL + '/api/v8'


class OAuth2Client:
    """
    A class representing a client interacting with the discord OAuth2 API.
    """

    def __init__(
        self,
        *,
        client_id: int,
        client_secret: str,
        redirect_uri: str,
        scopes: Optional[List[str]] = None,
    ):
        """A class representing a client interacting with the discord OAuth2 API.

        :param client_id: The OAuth application's client_id
        :type client_id: int
        :param client_secret: The OAuth application's client_secret
        :type client_secret: str
        :param redirect_uri: The OAuth application's redirect_uri. Must be from one of the configured uri's on the developer portal
        :type redirect_uri: str
        :param scopes: A list of OAuth2 scopes, defaults to None
        :type scopes: Optional[List[str]], optional
        """
        self._id = client_id
        self._auth = client_secret
        self._redirect = redirect_uri
        self._scopes = " ".join(scopes) if scopes is not None else None

        self.http = HTTPClient()
        self.http._state_info.update(
            {
                "client_id": self._id,
                "client_secret": self._auth,
                "redirect_uri": self._redirect,
                "scopes": self._scopes,
            }
        )

    def auth(self, state: Optional[str] = None, prompt: Optional[str] = None):
        client_id = f"client_id={self._id}"
        redirect_uri = f"redirect_uri={self._redirect}"
        scopes = f"scope={self._scopes}"
        response_type = "response_type=code"
        url = (
            DISCORD_URL
            + f"/api/oauth2/authorize?{client_id}&{redirect_uri}&{scopes}&{response_type}"
        )
        if state:
            url += f"&state={state}"
        if prompt:
            url += f"&prompt={prompt}"
        return url

    async def exchange_code(self, code: str) -> TokenResponse:
        """Exchanges the code you receive from the OAuth2 redirect.

        :param code: The code you've received from the OAuth2 redirect
        :type code: str
        :return: A response class containing information about the access token
        :rtype: AccessTokenResponse
        """
        route = Route("POST", "/oauth2/token")
        post_data = {
            "client_id": self._id,
            "client_secret": self._auth,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self._redirect,
        }
        if self._scopes is not None:
            post_data["scope"] = self._scopes
        resp = await self.http.request(route, data=post_data)
        token_resp = TokenResponse(data=resp)
        return token_resp

    async def refresh_token(
        self, refresh_token: str
    ) -> Dict[str, Any]:
        """Refreshes an access token. Takes either a string or an AccessTokenResponse.

        :param refresh_token: The refresh token you received when exchanging a redirect code
        :type refresh_token: Union[str, AccessTokenResponse]
        :return: A new access token response containg information about the refreshed access token
        :rtype: Dict[str, Any]
        """
        route = Route("POST", "/oauth2/token")
        post_data = {
            "client_id": self._id,
            "client_secret": self._auth,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        return await self.http.request(route, data=post_data)

    async def identify(
        self, token: Union[str, TokenResponse]
    ) -> User:
        """Makes an api call to fetch a user using their access token.

        :param access_token_response: A class holding information about an access token
        :type access_token_response: AccessTokenResponse
        :return: Returns a User object holding information about the select user
        :rtype: User
        """
        access_token = token
        if isinstance(access_token, TokenResponse):
            access_token = token.access_token

        route = Route("GET", "/users/@me")
        headers = {"Authorization": "Bearer {}".format(access_token)}
        resp = await self.http.request(route, headers=headers)
        user = User(http=self.http, data=resp, acr=token)
        return user

    async def guilds(self, token: Dict[str, Any]) -> Dict[str, Any]:
        access_token = token["access_token"]

        route = Route("GET", "/users/@me/guilds")
        headers = {"Authorization": "Bearer {}".format(access_token)}
        guilds = await self.http.request(route, headers=headers)
        return guilds

    async def close(self):
        """Closes and performs cleanup operations on the client, such as clearing its cache."""
        await self.http.close()
