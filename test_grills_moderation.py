#!/usr/bin/env python3
"""
Test OpenAI-powered moderation on r/grillsgonewild posts.
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Sample posts from r/grillsgonewild mod queue
test_posts = [
    {
        "author": "treybeau",
        "score": 1,
        "title": "Cynch.com get $15 off your first propane Tank Exchange.",
        "content": "",
        "type": "submission"
    },
    {
        "author": "Livilide", 
        "score": 1,
        "title": "How To Make Keto Grilled Pork Belly with Ssamjang Dipping Sauce| Easy Ke...",
        "content": "",
        "type": "submission"
    },
    {
        "author": "Most_Television5763",
        "score": 29,
        "title": "Do y'all like my new grills?",
        "content": "",
        "type": "submission"
    },
    {
        "author": "thatown2",
        "score": 1,
        "title": "BBQ Meal Prep Vegan and Keto",
        "content": "",
        "type": "submission"
    },
    {
        "author": "Bestflatyopgrills",
        "score": 1,
        "title": "best small grills reviews & buying guide",
        "content": "",
        "type": "submission"
    }
]

def analyze_post_with_ai(title, content, author, score):
    """
    Use OpenAI to analyze a post and decide if it should be approved or removed.
    
    Args:
        title: Post title
        content: Post content (may be empty for link posts)
        author: Username of the author
        score: Post score
        
    Returns:
        Dict with decision and reasoning
    """
    try:
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        post_text = f"Title: {title}"
        if content.strip():
            post_text += f"\nContent: {content}"
        
        prompt = f"""You are a Reddit moderator for r/grillsgonewild, a subreddit about BBQ grills and grilling equipment. Analyze this post and decide whether to APPROVE or REMOVE it.

Consider these factors for this grilling subreddit:
- Spam or promotional content (especially affiliate links, discount codes)
- Off-topic content (not about grills/grilling/BBQ)
- Self-promotion without community engagement
- Low-effort posts
- Legitimate grilling content should be approved

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
                {"role": "system", "content": "You are a helpful Reddit moderation assistant for a grilling subreddit. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=200
        )
        
        # Parse the response
        import json
        result = json.loads(response.choices[0].message.content)
        return result
        
    except Exception as e:
        print(f"Error analyzing post: {e}")
        return {"action": "APPROVE", "reason": f"Error in analysis: {e}", "confidence": 1}

def test_grills_moderation():
    """Test AI moderation on the r/grillsgonewild posts."""
    print("Testing OpenAI-powered moderation on r/grillsgonewild posts")
    print("=" * 65)
    
    for i, post in enumerate(test_posts, 1):
        print(f"\n--- POST {i} ---")
        print(f"Author: u/{post['author']}")
        print(f"Score: {post['score']}")
        print(f"Title: {post['title']}")
        if post['content']:
            print(f"Content: {post['content'][:100]}{'...' if len(post['content']) > 100 else ''}")
        print("\nAI Analysis:")
        
        # Get AI decision
        decision = analyze_post_with_ai(
            post['title'], 
            post['content'], 
            post['author'], 
            post['score']
        )
        
        # Display results
        action_emoji = "✅" if decision['action'] == 'APPROVE' else "❌"
        print(f"{action_emoji} Decision: {decision['action']}")
        print(f"Reason: {decision['reason']}")
        print(f"Confidence: {decision['confidence']}/10")
        print("-" * 50)

if __name__ == "__main__":
    test_grills_moderation()
