#!/usr/bin/env python3

import argparse
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
    CHUNK_SIZE = 125

    def __init__(self, username, access_token, opml_in=None, quiet=True, verbose=False):
        self.access_token = access_token
        self.quiet = quiet
        self.verbose = verbose
        self.feeds_in = []
        if opml_in:
            self.feeds_in = self.import_opml(opml_in)
        friends = self.fetch_friends(username)
        self.friends = []
        cursor = 0
        while cursor < len(friends):
            these_friends = friends[cursor : cursor + self.CHUNK_SIZE]
            cursor = cursor + self.CHUNK_SIZE
            asyncio.run(self.collect_feeds(these_friends))

    def __str__(self):
        document = OpmlDocument()
        friends_with_feeds = 0
        feeds_added = 0
        for friend in self.friends:
            self.status(f"{friend['username']}: {friend.get('feed', '-')}")
            if "feed" in friend:
                friends_with_feeds += 1
                if friend["feed"] not in self.feeds_in:
                    feeds_added += 1
                    document.add_rss(
                        friend["feed_title"] or friend["username"],
                        friend["feed"],
                    )
        pct = friends_with_feeds / len(self.friends) * 100
        self.status(
            f"Of {len(self.friends)} friends, {friends_with_feeds} have feeds ({pct:.3n}%)"
        )
        self.status(f"({feeds_added} feeds added)")
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
                    self.warn(f"Invalid cert for {url}: {str(exc)}")
                except Exception as exc:
                    self.warn(f"* Unknown error for {url}: {str(exc)}")
        return None

    def import_opml(self, filename):
        try:
            opml_in = OpmlDocument.load(filename)
        except Exception as exc:
            self.fatal(f"Can't load {filename}: {str(exc)}")
        return self.walk_outlines(opml_in.outlines)

    def walk_outlines(self, outlines):
        feeds = []
        for outline in outlines:
            if outline.xml_url:
                feeds.append(outline.xml_url)
            if outline.outlines:
                feeds = feeds + self.walk_outlines(outline.outlines)
        return feeds

    def status(self, message):
        if self.verbose:
            sys.stderr.write(f"{message}\n")

    def warn(self, message):
        if not self.quiet:
            sys.stderr.write(f"WARN: {message}\n")

    def fatal(self, message):
        sys.stderr.write(f"FATAL: {message}\n")
        sys.exit(1)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Validate and show data model of a Structured Field Value."
    )
    parser.add_argument(
        "-t",
        "--twitter",
        dest="twitter_username",
        help="Twitter username",
        required=True,
    )
    parser.add_argument(
        "-i",
        "--input_opml",
        dest="input_opml",
        help="OPML file input",
        default=False,
    )
    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument(
        "-q", "--quiet", dest="quiet", action="store_true", help="Suppress warnings"
    )
    verbosity.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        action="store_true",
        help="More verbose details",
    )

    return parser.parse_args()


if __name__ == "__main__":
    ACCESS_TOKEN = os.environ.get("TWITTER_ACCESS_TOKEN", None)
    if not ACCESS_TOKEN:
        sys.stderr.write("Set TWITTER_ACCESS_TOKEN in environment.\n")
        sys.exit(1)
    args = parse_args()
    print(
        FriendFeeder(
            args.twitter_username,
            ACCESS_TOKEN,
            args.input_opml,
            args.quiet,
            args.verbose,
        )
    )
