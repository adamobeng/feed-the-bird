# feed-the-bird

Make an RSS feed from your Twitter Home Timeline

# Prerequisites

- Python libraries:
    - oauth2
    - feedparser
    - feedgen
    - requests
- [Your Twitter access token](https://dev.twitter.com/oauth/overview/application-owner-access-tokens)

# Usage

1. Create a file at '~/.ftb.yaml' which looks like:

``` yaml
- {
    twitter: {
        screen_name : 'YOUR_SCREEN_NAME',
        consumer_key: 'YOUR_KEY',
        consumer_secret: 'YOUR_SECRET',
        access_token: 'YOUR_TOKEN',
        access_token_secret: 'YOUR_SECRET',
    },
    rss_file : '~/path/to/rss.xml'
}
```

2. Run ./ftb.py
