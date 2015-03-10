#!/usr/bin/env python
import yaml
import json
import oauth2 as oauth
import feedparser
import datetime
from dateutil import parser
from feedgen.feed import FeedGenerator


def pull_tweets(consumer_key, consumer_secret, access_token,
                access_token_secret, screen_name, count=200, since_id=None,
                max_iter=15):
    # http://stackoverflow.com/questions/6399978/getting-started-with-twitter-
    # oauth2-python
    consumer = oauth.Consumer(key=consumer_key, secret=consumer_secret)
    access_token = oauth.Token(key=access_token, secret=access_token_secret)
    client = oauth.Client(consumer, access_token)

    timeline_endpoint = (
        'https://api.twitter.com/1.1/statuses/home_timeline.json'
        '?contributor_details=True&count=%s' % (count))

    if since_id is not None:
        timeline_endpoint += '&since_id=%s' % since_id

    all_data = []

    response, data = client.request(timeline_endpoint)
    data = json.loads(data)

    if 'errors' in data:
        raise RuntimeError(data)
    ##

    max_id = None
    for i in range(max_iter):
        if min(t['id'] for t in data) == max_id:
            break
        max_id = min(t['id'] for t in data)
        print 'Fetching page', i, max_id
        response, data = client.request(
            timeline_endpoint + '&max_id=%s' % max_id)
        data = json.loads(data)
        if 'errors' not in data:
            all_data.extend(data)
        else:
            break
    return all_data

def make_feed(RSS_FILE, twitter_account):
    try:
        feed = feedparser.parse(RSS_FILE)
        since_id = feed.entries[0]['id'].split('/')[-1]
        print 'Getting tweets since', since_id
    except Exception as e:
        print e
        since_id = None

    tweets = pull_tweets(since_id=since_id, **twitter_account)
    fg = FeedGenerator()
    fg.id('https://twitter.com/' + twitter_account['screen_name'])
    fg.link({'href': 'https://twitter.com/' +
             CONFIG['twitter'][0]['screen_name'], 'rel': 'alternate'})
    fg.description(
        'Twitter home timeline for ' + twitter_account['screen_name'])

    fg.title('Twitter home timeline for %s' % twitter_account['screen_name'])

    for t in tweets:
        tweet_url = 'https://twitter.com/%s/status/%s' % (
            t['user']['id_str'], t['id_str'])
        fe = fg.add_entry()
        fe.summary(t['text'])
        fe.title('@' + t['user']['screen_name'] + ' (%s)' %
                 t['user']['name'] + ': ' + t['text'])
        fe.published(t['created_at'])
        fe.author({
            'name': t['user']['name'],
            'uri': '',
            'email': t['user']['screen_name']})

        fe.id(tweet_url)
        fe.link({'href': tweet_url, 'rel': 'alternate'})

        content = t['text']
        content += '<a href="https://twitter.com/intent/retweet?tweet_id=%s">Retweet</a><br/>' % t[
            'id_str']
        content += '<a href="https://twitter.com/intent/tweet?in-reply-to=%s&text=%s">Reply</a><br/>' % (
            t['id_str'], '%40' + t['user']['screen_name'])
        content += '<a href="https://twitter.com/intent/favorite?tweet_id=%s">Favorite</a><br/>' % t[
            'id_str']
        if 'entities' in t:
            if 'urls' in t['entities']:
                for u in t['entities']['urls']:
                    fe.link({'href': u['expanded_url'], 'rel': 'related'})
                    content += '\n<a href="%s">%s</a>' % (
                        u['expanded_url'], u['expanded_url'])

        fe.description(content)
    fg.rss_file(RSS_FILE)

if __name__ == '__main__':
    CONFIG = yaml.load(open('config.yaml'))
    print 'config:', CONFIG.keys()
    RSS_FILE = CONFIG['rss_file']

    twitter_account = CONFIG['twitter'][0]
    make_feed(RSS_FILE, twitter_account)
