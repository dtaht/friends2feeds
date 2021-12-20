#!/usr/bin/env python3

import asyncio
import os
import ssl
import sys
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import httpx
from opml import OpmlDocument


class FriendFeeder:
    TW_API = "https://api.twitter.com/2/users"
    TIMEOUT = 7
    FEED_TYPES = [
        "application/rss+xml",
        "application/atom+xml",
    ]
    CHUNK_SIZE = 25

    def __init__(self, username, access_token):
        self.access_token = access_token
        friends = self.fetch_friends(username)
        self.friends = []
        cursor = 0
        while cursor < len(friends):
            these_friends = friends[cursor : cursor + self.CHUNK_SIZE]
            cursor = cursor + self.CHUNK_SIZE
            asyncio.run(self.collect_feeds(these_friends))

    def __str__(self):
        document = OpmlDocument()
        for friend in self.friends:
            self.status(f"{friend['username']}: {friend.get('feed', '-')}")
            if "feed" in friend:
                document.add_rss(
                    friend["feed_title"] or friend["username"], friend["feed"],
                )
        return document.dumps(pretty=True)

    def fetch_friends(self, username):
        user_id = self.lookup_user(username)
        api_url = f"{self.TW_API}/{user_id}/following?max_results=1000&user.fields=username,url"
        friends = self.twitter_request(api_url)
        return friends

    def lookup_user(self, username):
        api_url = f"{self.TW_API}/by/username/{username}"
        response = self.twitter_request(api_url)
        return response["id"]

    def twitter_request(self, url, next_token=None):
        req_headers = {"Authorization": f"Bearer {self.access_token}"}
        if next_token:
            req_url = f"{url}&pagination_token={next_token}"
        else:
            req_url = url
        response = httpx.get(req_url, headers=req_headers, timeout=self.TIMEOUT)
        response_json = response.json()
        if response.status_code != 200:
            message = f"{response_json['title']} -- {response_json['detail']}"
            self.fatal(f"API response {response.status_code}: {message}")
        limit = response.headers.get("x-rate-limit-remaining", None)
        meta = response_json.get("meta", {})
        data = response_json["data"]
        if "next_token" in meta:
            data = data + self.twitter_request(url, meta["next_token"])
        return data

    async def collect_feeds(self, friends):
        responses = await asyncio.gather(*map(self.async_request, friends))
        self.friends = self.friends + list(map(self.get_feed, responses, friends))

    def get_feed(self, response, friend):
        if response is None or response.status_code != 200:
            return friend
        base = response.url
        soup = BeautifulSoup(response.text, "html.parser")
        for link in soup.find_all("link", type=self.FEED_TYPES):
            url = link.get("href", None)
            if url:
                friend["feed"] = urljoin(str(base), url, allow_fragments=False)
                friend["feed_title"] = link.get("title", None)
                break
        return friend

    async def async_request(self, friend):
        url = friend.get("url", None)
        if url:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                try:
                    return await client.get(url, timeout=self.TIMEOUT)
                except httpx.RequestError as exc:
                    self.warn(f"Request error to {exc.request.url}: {exc}")
                except ssl.SSLCertVerificationError as exc:
                    self.warn(f"Invalid cert for {url}")
                except Exception as exc:
                    self.warn(f"* Unknown error for {url}: {str(exc)}")
        return None

    def status(self, message):
        sys.stderr.write(f"{message}\n")

    def warn(self, message):
        sys.stderr.write(f"WARN: {message}\n")

    def fatal(self, message):
        sys.stderr.write(f"FATAL: {message}\n")
        sys.exit(1)


if __name__ == "__main__":
    ACCESS_TOKEN = os.environ.get("TWITTER_ACCESS_TOKEN", None)
    if not ACCESS_TOKEN:
        sys.stderr.write("Set TWITTER_ACCESS_TOKEN in environment.\n")
        sys.exit(1)
    print(FriendFeeder(sys.argv[1], ACCESS_TOKEN))
