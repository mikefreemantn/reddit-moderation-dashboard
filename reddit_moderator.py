#!/usr/bin/env python3
"""
Reddit Moderator Middle Man Bot

This bot monitors the mod queue for a specified subreddit and automatically
decides whether to approve or remove content based on analysis.
"""

import os
import time
import logging
import praw
from dotenv import load_dotenv
from typing import Optional, Dict, Any
import re

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('reddit_moderator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class RedditModerator:
    """Reddit Moderator Bot for automated content moderation."""
    
    def __init__(self):
        """Initialize the Reddit moderator bot."""
        self.reddit = self._authenticate()
        self.subreddit_name = os.getenv('SUBREDDIT_NAME', 'complainaboutanything')
        self.subreddit = self.reddit.subreddit(self.subreddit_name)
        
        # Verify bot has moderator permissions
        self._verify_permissions()
        
    def _authenticate(self) -> praw.Reddit:
        """Authenticate with Reddit API using PRAW."""
        try:
            reddit = praw.Reddit(
                client_id=os.getenv('REDDIT_CLIENT_ID'),
                client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
                username=os.getenv('REDDIT_USERNAME'),
                password=os.getenv('REDDIT_PASSWORD'),
                user_agent=os.getenv('REDDIT_USER_AGENT')
            )
            
            # Test authentication
            user = reddit.user.me()
            logger.info(f"Successfully authenticated as: {user}")
            return reddit
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise
    
    def _verify_permissions(self):
        """Verify the bot has moderator permissions for the subreddit."""
        try:
            # Try to access moderator features
            list(self.subreddit.mod.modqueue(limit=1))
            logger.info(f"Successfully verified moderator permissions for r/{self.subreddit_name}")
        except Exception as e:
            logger.error(f"No moderator permissions for r/{self.subreddit_name}: {e}")
            raise
    
    def analyze_content(self, item) -> Dict[str, Any]:
        """
        Analyze content to determine if it should be approved or removed.
        
        Args:
            item: Reddit submission or comment object
            
        Returns:
            Dict containing decision and reasoning
        """
        # Get content text
        if hasattr(item, 'selftext'):  # Submission
            content = f"{item.title} {item.selftext}".lower()
        else:  # Comment
            content = item.body.lower()
        
        # Basic content analysis rules
        decision = self._apply_moderation_rules(content, item)
        
        return decision
    
    def _apply_moderation_rules(self, content: str, item) -> Dict[str, Any]:
        """
        Apply moderation rules to determine action.
        
        Args:
            content: Lowercase content text
            item: Reddit item object
            
        Returns:
            Dict with 'action' ('approve' or 'remove') and 'reason'
        """
        # Rule 1: Remove obvious spam patterns
        spam_patterns = [
            r'buy now',
            r'click here',
            r'limited time offer',
            r'make money fast',
            r'www\.[a-zA-Z0-9-]+\.[a-zA-Z]{2,}',  # URLs
            r'http[s]?://',
        ]
        
        for pattern in spam_patterns:
            if re.search(pattern, content):
                return {
                    'action': 'remove',
                    'reason': f'Spam detected: matches pattern "{pattern}"'
                }
        
        # Rule 2: Remove excessive profanity or hate speech
        hate_words = [
            'hate', 'kill yourself', 'kys', 'die',
            # Add more as needed, but be careful with false positives
        ]
        
        hate_count = sum(1 for word in hate_words if word in content)
        if hate_count >= 2:
            return {
                'action': 'remove',
                'reason': f'Excessive hate speech detected ({hate_count} instances)'
            }
        
        # Rule 3: Remove very short posts that are likely low effort
        if hasattr(item, 'selftext') and len(content.strip()) < 10:
            return {
                'action': 'remove',
                'reason': 'Post too short, likely low effort'
            }
        
        # Rule 4: Remove posts with excessive caps (>50% uppercase)
        if len(content) > 10:
            caps_ratio = sum(1 for c in content if c.isupper()) / len(content)
            if caps_ratio > 0.5:
                return {
                    'action': 'remove',
                    'reason': 'Excessive caps lock usage'
                }
        
        # Rule 5: Approve everything else
        return {
            'action': 'approve',
            'reason': 'Content passed all moderation checks'
        }
    
    def moderate_item(self, item):
        """
        Moderate a single item from the mod queue.
        
        Args:
            item: Reddit submission or comment object
        """
        try:
            # Analyze the content
            decision = self.analyze_content(item)
            
            # Log the decision
            item_type = "submission" if hasattr(item, 'selftext') else "comment"
            logger.info(f"Analyzing {item_type} by u/{item.author}: {decision['action']} - {decision['reason']}")
            
            # Take action
            if decision['action'] == 'approve':
                item.mod.approve()
                logger.info(f"✅ Approved {item_type} by u/{item.author}")
            elif decision['action'] == 'remove':
                item.mod.remove()
                # Optionally send removal reason
                if hasattr(item, 'reply'):  # Can reply to this item
                    try:
                        removal_message = f"Your {item_type} was automatically removed: {decision['reason']}"
                        item.reply(removal_message).mod.distinguish(sticky=True)
                    except Exception as e:
                        logger.warning(f"Could not send removal message: {e}")
                logger.info(f"❌ Removed {item_type} by u/{item.author}")
            
        except Exception as e:
            logger.error(f"Error moderating item: {e}")
    
    def monitor_mod_queue(self, check_interval: int = 300):
        """
        Continuously monitor the mod queue and process items.
        
        Args:
            check_interval: Seconds between checks (default 5 minutes)
        """
        logger.info(f"Starting mod queue monitoring for r/{self.subreddit_name}")
        logger.info(f"Check interval: {check_interval} seconds ({check_interval//60} minutes)")
        logger.info("⚠️  Using conservative API rate limiting to respect Reddit's limits")
        
        while True:
            try:
                # Get items from mod queue (reduced limit)
                mod_queue_items = list(self.subreddit.mod.modqueue(limit=5))
                
                if mod_queue_items:
                    logger.info(f"Found {len(mod_queue_items)} items in mod queue")
                    
                    for item in mod_queue_items:
                        self.moderate_item(item)
                        time.sleep(3)  # Increased rate limiting between actions
                else:
                    logger.info("Mod queue is empty")
                
                # Wait before next check
                logger.info(f"Waiting {check_interval} seconds before next check...")
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                logger.info("Bot stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                logger.info(f"Waiting {check_interval} seconds before retry...")
                time.sleep(check_interval)
    
    def test_connection(self):
        """Test the bot's connection and permissions."""
        try:
            logger.info("Testing Reddit connection...")
            user = self.reddit.user.me()
            logger.info(f"✅ Connected as: {user}")
            
            logger.info(f"Testing subreddit access for r/{self.subreddit_name}...")
            sub_info = self.subreddit.display_name
            logger.info(f"✅ Can access r/{sub_info}")
            
            logger.info("Testing mod queue access...")
            queue_count = len(list(self.subreddit.mod.modqueue(limit=5)))
            logger.info(f"✅ Mod queue accessible, {queue_count} items found")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Connection test failed: {e}")
            return False


def main():
    """Main function to run the Reddit moderator bot."""
    try:
        # Initialize the bot
        bot = RedditModerator()
        
        # Test connection first
        if not bot.test_connection():
            logger.error("Connection test failed. Please check your credentials and permissions.")
            return
        
        # Start monitoring with conservative rate limiting
        bot.monitor_mod_queue(check_interval=300)
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")


if __name__ == "__main__":
    main()
