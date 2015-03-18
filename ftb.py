#!/usr/bin/env python
import yaml
import json
import oauth2 as oauth
import feedparser
import datetime
from dateutil import parser
from feedgen.feed import FeedGenerator
import subprocess
import os.path
import requests
import tldextract

def unshorten(url):
    if len(tldextract.extract(url).suffix) > 2:
        return url
    try:
        r = requests.head(url)
        if str(r.status_code)[0] == '3':
            return r.headers['location']
        else:
            return url
    except Exception as e:
        print url, e
        return url

def pull_tweets(consumer_key, consumer_secret, access_token,
                access_token_secret, screen_name, list_slug=None, since_id=None,
                max_iter=15, mentions=False):
    # http://stackoverflow.com/questions/6399978/getting-started-with-twitter-
    # oauth2-python
    consumer = oauth.Consumer(key=consumer_key, secret=consumer_secret)
    access_token = oauth.Token(key=access_token, secret=access_token_secret)
    client = oauth.Client(consumer, access_token)

    if list_slug is not None:
        timeline_endpoint = (
            'https://api.twitter.com/1.1/lists/statuses.json'
            '?slug=%s&owner_screen_name=%s&count=200' % (list_slug, screen_name))
    elif mentions:
        timeline_endpoint = 'https://api.twitter.com/1.1/statuses/mentions_timeline.json?count=200&contributor_details=true&include_entities=true'
    else:
        timeline_endpoint = (
            'https://api.twitter.com/1.1/statuses/home_timeline.json'
            '?contributor_details=True&count=200')

    if since_id is not None:
        timeline_endpoint += '&since_id=%s' % since_id


    response, data = client.request(timeline_endpoint)
    data = json.loads(data)

    if 'errors' in data:
        raise RuntimeError(data)
    if data == []:
        print 'No tweets returned'
        return []
    ##

    all_data = []
    all_data.extend(data)

    max_id = None
    for i in range(max_iter):
        if min(t['id'] for t in data) == max_id:
            break
        max_id = min(t['id'] for t in data)
        print 'Fetching page', i, 'before', max_id, list(t['created_at'] for t in data if t['id'] == max_id)[0]
        response, data = client.request(
            timeline_endpoint + '&max_id=%s' % max_id)
        data = json.loads(data)
        if 'errors' not in data:
            all_data.extend(data)
        else:
            break
    return all_data

def make_feed(RSS_FILE, twitter_account, get_images):
    try:
        feed = feedparser.parse(RSS_FILE)
        since_id = feed.entries[0]['id'].split('/')[-1]
        print 'Getting tweets since', since_id, feed.entries[0]['published']
    except Exception as e:
        print e
        since_id = None

    tweets = pull_tweets(since_id=since_id, **twitter_account)
    if tweets==[]: return

    fg = FeedGenerator()
    if 'list_slug' in twitter_account:
        feed_url = 'https://twitter.com/%s/lists/%s' % (twitter_account['screen_name'], twitter_account['list_slug'])
        fg.description('Twitter home timeline for list %s ' + twitter_account['list_slug'])
        fg.title('Twitter home timeline for %s' % twitter_account['list_slug'])
    elif 'mentions' in twitter_account:
        if twitter_account['mentions']:
            feed_url = 'https://twitter.com/' + twitter_account['screen_name']
            fg.description(
                'Twitter mentions for ' + twitter_account['screen_name'])
            fg.title('Twitter mentions for %s' % twitter_account['screen_name'])

    else:
        feed_url = 'https://twitter.com/' + twitter_account['screen_name']
        fg.description(
            'Twitter home timeline for ' + twitter_account['screen_name'])
        fg.title('Twitter home timeline for %s' % twitter_account['screen_name'])

    fg.id(feed_url)
    fg.link({'href': feed_url, 'rel': 'alternate'})

    for t in tweets:
        tweet_url = 'https://twitter.com/%s/status/%s' % (
            t['user']['id_str'], t['id_str'])
        print 'Got tweet', tweet_url, t['created_at']
        fe = fg.add_entry()
        title = '@' + t['user']['screen_name'] + ' (%s)' % t['user']['name'] + ': ' + t['text']
        fe.published(t['created_at'])
        fe.author({
            'name': t['user']['name'],
            'uri': '',
            'email': t['user']['screen_name']})

        fe.id(tweet_url)
        fe.link({'href': tweet_url, 'rel': 'alternate'})

        content = t['text']
        content += '<br /><br /><a href="https://twitter.com/intent/retweet?tweet_id=%s">Retweet</a>' % t[
            'id_str']
        content += '<a href="https://twitter.com/intent/tweet?in_reply_to=%s%%26text=%s">Reply</a>' % (
            t['id_str'], '%40' + t['user']['screen_name'])
        content += '<a href="https://twitter.com/intent/favorite?tweet_id=%s">Favorite</a><br /><br />' % t[
            'id_str']

        if 'entities' in t:
            if ('media' in t['entities']) and get_images:
                for u in t['entities']['media']:
                    if u['type'] == 'photo':
                        curl = subprocess.Popen(['curl', u['media_url']], stdout = subprocess.PIPE)
                        mogrify = subprocess.Popen(['mogrify', '-format', 'jpeg', '-', '-'] , stdout = subprocess.PIPE, stdin=curl.stdout)
                        jp2a = subprocess.Popen(['jp2a', '-i', '--html', '--width=120', '-'], stdout = subprocess.PIPE, stdin=mogrify.stdout)
                        img = jp2a.communicate()[0]
                        content += img
                        content += '\n<a href="%s">%s</a><br />\n' % (
                        u['media_url'], u['media_url'])


            if 'urls' in t['entities']:
                for u in t['entities']['urls']:
                    current_url = unshorten(u['expanded_url'])
                    fe.link({'href': current_url, 'rel': 'related'})
                    content += '\n<a href="%s">%s</a><br />\n' % (current_url, current_url)
                    content = content.replace(u['url'],current_url)
                    title = title.replace(u['url'],current_url)

        fe.title(title)
        fe.description(content)
    return fg

if __name__ == '__main__':
    CONFIG = yaml.load(open(os.path.expanduser('~/.ftb-config.yaml')))

    for c in CONFIG['accounts']:
        RSS_FILE = c['rss_file']
        twitter_account = c['twitter']
        get_images = c['get_images'] if 'get_images' in c else False
        fg = make_feed(RSS_FILE, twitter_account, get_images)
        if fg:
            new_len = len(feedparser.parse(fg.rss_str()))
        else:
            new_len=0
            print new_len, 'new entries'
            break

        old_feed = feedparser.parse(RSS_FILE)
        print len(old_feed.entries), 'old entries'
        for e in old_feed.entries:
            fe = fg.add_entry()
            fe.published(e['published'])
            fe.author(e['author_detail'])
            fe.id(e['id'])
            fe.title(e['title'])
            fe.description(e['summary'])
            for l in e['links']:
                fe.link(l)

        fg.rss_file(RSS_FILE)
