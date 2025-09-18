#!/usr/bin/env python3
"""
Test OpenAI-powered moderation on the sample comments from mod queue.
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Sample comments from the mod queue
test_comments = [
    {
        "author": "ruiyanglol2",
        "score": -2,
        "content": "Yes and that's why the democrats won for decades!!!!Now you've become so unhinged that it seems like MAGA is more reasonable and common sense than Leftists. Charlie doesn't represent Hitler, he befame the majority/common folk. YOU became the Killer. What do you not get?"
    },
    {
        "author": "haydesigner", 
        "score": 5,
        "content": "Now you sound unhinged. You're acting like the conservatives haven't been doing this for decades now. You're conveniently, forgetting all the bombast and antagonism overwhelmingly done by conservatives for quite some time now. Spinning it as \"any murder is horrible\" pearl-clutching is an act of bad faith by you. **Conservatives are the ones with the ownership of hatred, racism, misogyny, homophobia.** That history, short *and* long, doesn't get erased just because one right winger killed anoth..."
    }
]

def analyze_comment_with_ai(comment_text, author, score):
    """
    Use OpenAI to analyze a comment and decide if it should be approved or removed.
    
    Args:
        comment_text: The comment content
        author: Username of the author
        score: Comment score
        
    Returns:
        Dict with decision and reasoning
    """
    try:
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        prompt = f"""You are a Reddit moderator for r/complainaboutanything. Analyze this comment and decide whether to APPROVE or REMOVE it.

Consider these factors:
- Hate speech or harassment
- Personal attacks
- Spam or promotional content
- Threats or violence
- Misinformation
- Rule violations

The subreddit allows complaints and political discussion, but not harassment or hate speech.

Comment by u/{author} (Score: {score}):
"{comment_text}"

Respond with a JSON object containing:
- "action": "APPROVE" or "REMOVE"
- "reason": Brief explanation of your decision
- "confidence": Number from 1-10 (10 = very confident)

Example response:
{{"action": "APPROVE", "reason": "Political opinion within acceptable bounds", "confidence": 7}}"""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful Reddit moderation assistant. Always respond with valid JSON."},
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
        print(f"Error analyzing comment: {e}")
        return {"action": "APPROVE", "reason": f"Error in analysis: {e}", "confidence": 1}

def test_ai_moderation():
    """Test AI moderation on the sample comments."""
    print("Testing OpenAI-powered moderation on mod queue comments")
    print("=" * 60)
    
    for i, comment in enumerate(test_comments, 1):
        print(f"\n--- COMMENT {i} ---")
        print(f"Author: u/{comment['author']}")
        print(f"Score: {comment['score']}")
        print(f"Content: {comment['content'][:100]}{'...' if len(comment['content']) > 100 else ''}")
        print("\nAI Analysis:")
        
        # Get AI decision
        decision = analyze_comment_with_ai(
            comment['content'], 
            comment['author'], 
            comment['score']
        )
        
        # Display results
        action_emoji = "✅" if decision['action'] == 'APPROVE' else "❌"
        print(f"{action_emoji} Decision: {decision['action']}")
        print(f"Reason: {decision['reason']}")
        print(f"Confidence: {decision['confidence']}/10")
        print("-" * 40)

if __name__ == "__main__":
    test_ai_moderation()
