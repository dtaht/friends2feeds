
# Friends2Feeds: Taking Feeds Back from Social Media

Long ago (in Internet time), people used _feeds_ to stay up-to-date with what happened on the Web. Then came big platforms who took that concept (and sometimes the word itself) and made everyone believe that it was better when there were lots of ads in it and an algorithm choosing what you saw.

We can do better. Social media might be suitable for some purposes, but often you want to make sure you see _every_ post from a particular person, organisation, or project. Feed readers are a better fit for this, but feed discovery is cumbersome -- we've become conditioned to the instant gratification of hitting 'follow' rather than taking the time to hunt down a feed and hooking it up in a feed reader.

Friends2Feeds helps to reverse this tendency, by searching the people you follow on social media (specifically Twitter, to start with) and creating an OPML file from any feeds it finds, so that you can easily import them into your feed reader. Then you can decide whether or not you need to follow all of those social media accounts.


## Installation

If you already have [Python](https://www.python.org) on your system, it's as easy as:

~~~ shell
> pip3 install friends2feeds
~~~


## Creating an OPML File

`friends2feeds.py` takes a Twitter username as the `-t` option, and outputs an OPML file for that person's friends. For example:

~~~ shell
> TWITTER_ACCESS_TOKEN=MY_TOKEN friends2feeds.py -t mnot > friends.opml
~~~

Then, import that OPML file to your feed reader.

Note that `TWITTER_ACCESS_TOKEN` needs to be in the environment, carrying your twitter API access token. To get one, you'll need to:

1. Sign up for a [Twitter developer account](https://developer.twitter.com/en)
2. Create a new project
3. Create a new app within that project
4. Go to the "Keys and Tokens" tab and copy down the Bearer Token (generating a new one if necessary).

In the example above, the token is `MY_TOKEN`; yours is likely to be considerably longer than that.


## Updating Your Feeds

Over time, you might follow new people, and the people you follow might add new feeds. To update your feed reader without adding a lot of duplicates, you can use the `-i` flag to specify the location of your old OPML file (either an export from your feed reader, or preferably the last OPML file you generated with friends2feeds); all of the feeds in it will be excluded from the output:

~~~ shell
> TWITTER_ACCESS_TOKEN=MY_TOKEN friends2feeds.py -t mnot -i old.opml > friends.opml
~~~
