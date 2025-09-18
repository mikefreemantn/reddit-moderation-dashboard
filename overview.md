1. Make a Reddit app

Go to https://www.reddit.com/prefs/apps
 (while logged in).

Scroll to the bottom and click Create App or Create Another App.

Fill in:

name: something like AutoModWebhookBot

app type: “script”

redirect uri: http://localhost:8080 (you won’t actually use it for a script, but Reddit requires a value)

description, about url: optional

Click create app.
You’ll now see:

A client ID (under the app name).

A client secret.

2. Get API credentials

You’ll need:

client_id (from above)

client_secret (from above)

username (the Reddit account you’ll run the bot as)

password (for that account)

user_agent (any string that identifies your app, e.g. "automod-webhook-forwarder/0.1 by u/YourRedditUsername")

3. Install PRAW (Python wrapper)
pip install praw requests

4. Authenticate

Here’s a minimal test script:

import praw

reddit = praw.Reddit(
    client_id="n9pJBYrefEhUn3qkOD2oHQ",
    client_secret="Mi-PdkWlv561rA7l6IxhvE-dHw252w
",
    username="bigmur72",
    password="1Digigraph!",
    user_agent="automod-webhook-forwarder/0.1 by u/YOUR_USERNAME"
)

print(reddit.user.me())  # should print your bot account name

5. Access the modlog

Once authenticated, you can do things like:

sub = reddit.subreddit("YourSubredditName")

for log in sub.mod.log(limit=10):
    print(log.mod, log.action, log.target_author, log.target_permalink)


That’s how you can pick up AutoModerator actions and then forward them to a webhook.

6. Send to a webhook

Add requests.post where you want:

import requests

WEBHOOK_URL = "https://your-webhook-endpoint.com"

for log in sub.mod.stream.log(skip_existing=True):
    if log.mod == "AutoModerator" and log.action in ("removelink", "removecomment"):
        payload = {
            "action": log.action,
            "reason": log.details,
            "target_author": log.target_author,
            "permalink": f"https://reddit.com{log.target_permalink}"
        }
        requests.post(WEBHOOK_URL, json=payload, timeout=5)
