# Reddit Moderator Middle Man Bot

An automated Reddit moderation bot that monitors the mod queue for a specified subreddit and automatically decides whether to approve or remove content based on configurable rules.

## Features

- **Automated Moderation**: Continuously monitors the mod queue and takes action on posts/comments
- **Content Analysis**: Uses pattern matching and rule-based analysis to make moderation decisions
- **Logging**: Comprehensive logging of all actions and decisions
- **Rate Limiting**: Built-in delays to respect Reddit's API limits
- **Error Handling**: Robust error handling with automatic recovery

## Setup

### 1. Create a Reddit App

1. Go to https://www.reddit.com/prefs/apps (while logged in)
2. Scroll to the bottom and click "Create App" or "Create Another App"
3. Fill in:
   - **name**: `AutoModWebhookBot` (or similar)
   - **app type**: "script"
   - **redirect uri**: `http://localhost:8080`
   - **description**: Optional
4. Click "Create app"
5. Note down your **client ID** (under the app name) and **client secret**

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your Reddit credentials:
   ```
   REDDIT_CLIENT_ID=your_client_id_here
   REDDIT_CLIENT_SECRET=your_client_secret_here
   REDDIT_USERNAME=your_reddit_username
   REDDIT_PASSWORD=your_reddit_password
   REDDIT_USER_AGENT=reddit-moderator-bot/1.0 by u/your_username
   SUBREDDIT_NAME=complainaboutanything
   ```

### 4. Run the Bot

```bash
python reddit_moderator.py
```

## Moderation Rules

The bot currently implements these rules:

1. **Spam Detection**: Removes posts with spam patterns (buy now, URLs, etc.)
2. **Hate Speech**: Removes content with excessive hate speech
3. **Low Effort**: Removes very short posts
4. **Caps Lock**: Removes posts with excessive uppercase text
5. **Default**: Approves content that passes all checks

## Customization

You can modify the moderation rules in the `_apply_moderation_rules()` method in `reddit_moderator.py`.

## Logs

All bot activity is logged to:
- Console output
- `reddit_moderator.log` file

## Safety Features

- Connection testing before starting
- Permission verification
- Rate limiting between actions
- Comprehensive error handling
- Graceful shutdown on Ctrl+C
