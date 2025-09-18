#!/usr/bin/env python3
"""
Actually moderate Reddit posts - approve or remove based on AI analysis.
"""

import os
import time
import praw
from openai import OpenAI
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

def analyze_with_ai(title, content, author, score, subreddit_name):
    """
    Use OpenAI to analyze content and decide if it should be approved or removed.
    """
    try:
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        post_text = f"Title: {title}"
        if content and content.strip():
            post_text += f"\nContent: {content}"
        
        # Customize prompt based on subreddit
        if subreddit_name == 'grillsgonewild':
            context = "r/grillsgonewild, a subreddit about BBQ grills and grilling equipment"
            rules = """- Spam or promotional content (especially affiliate links, discount codes)
- Off-topic content (not about grills/grilling/BBQ)
- Self-promotion without community engagement
- Low-effort posts
- Legitimate grilling content should be approved"""
        else:
            context = f"r/{subreddit_name}"
            rules = """- Hate speech or harassment
- Personal attacks
- Spam or promotional content
- Threats or violence
- Misinformation
- Rule violations"""
        
        prompt = f"""You are a Reddit moderator for {context}. Analyze this post and decide whether to APPROVE or REMOVE it.

Consider these factors:
{rules}

Post by u/{author} (Score: {score}):
{post_text}

Respond with a JSON object containing:
- "action": "APPROVE" or "REMOVE"
- "reason": Brief explanation of your decision
- "confidence": Number from 1-10 (10 = very confident)

Example response:
{{"action": "REMOVE", "reason": "Promotional content with discount code", "confidence": 9}}"""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful Reddit moderation assistant. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=200
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
        
    except Exception as e:
        print(f"Error analyzing content: {e}")
        return {"action": "APPROVE", "reason": f"Error in analysis: {e}", "confidence": 1}

def moderate_subreddit(subreddit_name, limit=5, dry_run=False):
    """
    Moderate posts in a subreddit using AI analysis.
    
    Args:
        subreddit_name: Name of subreddit to moderate
        limit: Number of posts to process
        dry_run: If True, only show what would be done without taking action
    """
    try:
        # Authenticate with Reddit
        reddit = praw.Reddit(
            client_id=os.getenv('REDDIT_CLIENT_ID'),
            client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
            username=os.getenv('REDDIT_USERNAME'),
            password=os.getenv('REDDIT_PASSWORD'),
            user_agent=os.getenv('REDDIT_USER_AGENT')
        )
        
        subreddit = reddit.subreddit(subreddit_name)
        
        print(f"{'[DRY RUN] ' if dry_run else ''}Moderating r/{subreddit_name}")
        print("=" * 60)
        
        # Get items from mod queue
        mod_queue_items = list(subreddit.mod.modqueue(limit=limit))
        
        if not mod_queue_items:
            print("Mod queue is empty!")
            return
        
        print(f"Found {len(mod_queue_items)} items in mod queue")
        
        for i, item in enumerate(mod_queue_items, 1):
            print(f"\n--- ITEM {i} ---")
            
            # Get item details
            item_type = "submission" if hasattr(item, 'selftext') else "comment"
            author = str(item.author) if item.author else "[deleted]"
            
            if item_type == "submission":
                title = item.title
                content = item.selftext
                print(f"Post: {title}")
                print(f"Author: u/{author} | Score: {item.score}")
            else:
                title = f"Comment on: {item.submission.title[:50]}..."
                content = item.body
                print(f"Comment: {content[:100]}{'...' if len(content) > 100 else ''}")
                print(f"Author: u/{author} | Score: {item.score}")
            
            # Analyze with AI
            print("🤖 AI Analysis:", end=" ")
            decision = analyze_with_ai(title, content, author, item.score, subreddit_name)
            
            action_emoji = "✅" if decision['action'] == 'APPROVE' else "❌"
            print(f"{action_emoji} {decision['action']}")
            print(f"Reason: {decision['reason']}")
            print(f"Confidence: {decision['confidence']}/10")
            
            # Take action (unless dry run)
            if not dry_run:
                try:
                    if decision['action'] == 'APPROVE':
                        item.mod.approve()
                        print("✅ Post APPROVED")
                    elif decision['action'] == 'REMOVE':
                        item.mod.remove()
                        print("❌ Post REMOVED")
                        
                        # Add removal reason as mod note
                        try:
                            if hasattr(item, 'mod') and hasattr(item.mod, 'note'):
                                item.mod.note = f"Auto-removed: {decision['reason']}"
                        except:
                            pass  # Some items don't support mod notes
                    
                    time.sleep(2)  # Rate limiting
                    
                except Exception as e:
                    print(f"❗ Error taking action: {e}")
            else:
                print(f"[DRY RUN] Would {decision['action'].lower()} this item")
            
            print("-" * 50)
        
        print(f"\n{'[DRY RUN] ' if dry_run else ''}Moderation complete!")
        
    except Exception as e:
        print(f"Error: {e}")

def main():
    """Main function with options."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python moderate_posts.py <subreddit> [limit] [--dry-run]")
        print("Example: python moderate_posts.py grillsgonewild 5 --dry-run")
        return
    
    subreddit_name = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 5
    dry_run = '--dry-run' in sys.argv
    
    if dry_run:
        print("🔍 DRY RUN MODE - No actual moderation actions will be taken")
        print()
    
    moderate_subreddit(subreddit_name, limit, dry_run)

if __name__ == "__main__":
    main()
