#!/usr/bin/env python3
"""
Quick script to check what's in the mod queue without taking any actions.
"""

import os
import praw
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_mod_queue():
    """Check the top 2 items in the mod queue."""
    try:
        # Authenticate
        reddit = praw.Reddit(
            client_id=os.getenv('REDDIT_CLIENT_ID'),
            client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
            username=os.getenv('REDDIT_USERNAME'),
            password=os.getenv('REDDIT_PASSWORD'),
            user_agent=os.getenv('REDDIT_USER_AGENT')
        )
        
        subreddit = reddit.subreddit('grillsgonewild')
        
        print(f"Checking mod queue for r/grillsgonewild...")
        print("=" * 60)
        
        # Get top 5 items from mod queue
        mod_queue_items = list(subreddit.mod.modqueue(limit=5))
        
        if not mod_queue_items:
            print("Mod queue is empty!")
            return
        
        for i, item in enumerate(mod_queue_items, 1):
            print(f"\n--- ITEM {i} ---")
            print(f"Type: {'Submission' if hasattr(item, 'selftext') else 'Comment'}")
            print(f"Author: u/{item.author}")
            print(f"Created: {item.created_utc}")
            print(f"Score: {item.score}")
            
            if hasattr(item, 'selftext'):  # Submission
                print(f"Title: {item.title}")
                print(f"Content: {item.selftext[:500]}{'...' if len(item.selftext) > 500 else ''}")
                print(f"URL: https://reddit.com{item.permalink}")
            else:  # Comment
                print(f"Comment: {item.body[:500]}{'...' if len(item.body) > 500 else ''}")
                print(f"URL: https://reddit.com{item.permalink}")
            
            print("-" * 40)
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_mod_queue()
