#!/usr/bin/env python3
"""
Reddit Moderation Dashboard - Web Interface
"""
import requests
from openai import OpenAI
import os
import time
import json
import base64
import requests
import secrets
import urllib.parse
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_socketio import SocketIO, emit
import logging
import base64
from dotenv import load_dotenv
import threading

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(16))
socketio = SocketIO(app, cors_allowed_origins="*")

class ModerationDashboard:
    def __init__(self):
        self.reddit = None
        self.openai_client = None
        self.is_running = False
        self.current_subreddit = None
        self.current_username = None
        self.reddit_client_id = None
        self.reddit_client_secret = None
        self.reddit_username = None
        self.reddit_password = None
        self.reddit_token = None
        self.subreddit_cache = {}
        self.cache_timestamp = None
        
    def authenticate(self, credentials=None):
        """Authenticate with Reddit and OpenAI APIs using direct requests"""
        try:
            # Get credentials from request or environment
            if credentials:
                reddit_client_id = credentials.get('reddit_client_id')
                reddit_client_secret = credentials.get('reddit_client_secret')
                reddit_username = credentials.get('reddit_username')
                reddit_password = credentials.get('reddit_password')
                openai_api_key = credentials.get('openai_api_key')
            else:
                reddit_client_id = os.getenv('REDDIT_CLIENT_ID')
                reddit_client_secret = os.getenv('REDDIT_CLIENT_SECRET')
                reddit_username = os.getenv('REDDIT_USERNAME')
                reddit_password = os.getenv('REDDIT_PASSWORD')
                openai_api_key = os.getenv('OPENAI_API_KEY')
            
            # Validate required credentials
            if not all([reddit_client_id, reddit_client_secret, reddit_username, reddit_password, openai_api_key]):
                missing = []
                if not reddit_client_id: missing.append('Reddit Client ID')
                if not reddit_client_secret: missing.append('Reddit Client Secret')
                if not reddit_username: missing.append('Reddit Username')
                if not reddit_password: missing.append('Reddit Password')
                if not openai_api_key: missing.append('OpenAI API Key')
                return False, f"Missing credentials: {', '.join(missing)}"
            
            # Store credentials
            self.reddit_client_id = reddit_client_id
            self.reddit_client_secret = reddit_client_secret
            self.reddit_username = reddit_username
            self.reddit_password = reddit_password
            
            # Get Reddit OAuth token for web app using client credentials
            auth_string = base64.b64encode(f"{reddit_client_id}:{reddit_client_secret}".encode()).decode()
            headers = {
                'Authorization': f'Basic {auth_string}',
                'User-Agent': f'web:reddit-moderation-dashboard:v1.0 (by /u/{reddit_username})'
            }
            data = {
                'grant_type': 'client_credentials'
            }
            
            response = requests.post('https://www.reddit.com/api/v1/access_token', 
                                   headers=headers, data=data, timeout=30)
            
            if response.status_code != 200:
                return False, f"Reddit authentication failed: {response.text}"
            
            token_data = response.json()
            self.reddit_token = token_data.get('access_token')
            
            if not self.reddit_token:
                return False, "Failed to get Reddit access token"
            
            # Test Reddit API access
            reddit_headers = {
                'Authorization': f'Bearer {self.reddit_token}',
                'User-Agent': f'reddit-moderator-bot/2.0 by u/{reddit_username}'
            }
            
            me_response = requests.get('https://oauth.reddit.com/api/v1/me', headers=reddit_headers)
            if me_response.status_code != 200:
                return False, f"Reddit API test failed: {me_response.text}"
            
            user_data = me_response.json()
            self.current_username = user_data.get('name', reddit_username)
            
            # Store OpenAI API key (initialize client only when needed)
            self.openai_api_key = openai_api_key
            
            return True, f"Connected as u/{self.current_username}"
            
        except Exception as e:
            self.reddit = None
            self.openai_client = None
            self.current_username = None
            return False, str(e)
    
    def get_moderated_subreddits(self):
        """Get list of subreddits the user moderates using direct Reddit API with caching."""
        try:
            if not hasattr(self, 'reddit_token') or not self.reddit_token:
                return []
            
            # Check cache (valid for 5 minutes)
            current_time = time.time()
            if (hasattr(self, 'cache_timestamp') and self.cache_timestamp and 
                current_time - self.cache_timestamp < 300 and 
                hasattr(self, 'subreddit_cache') and self.subreddit_cache):
                return self.subreddit_cache
            
            headers = {
                'Authorization': f'Bearer {self.reddit_token}',
                'User-Agent': f'web:reddit-moderation-dashboard:v1.0 (by /u/{self.reddit_username})'
            }
            
            # Get subreddits where user is a moderator with timeout
            response = requests.get('https://oauth.reddit.com/subreddits/mine/moderator', 
                                  headers=headers, timeout=30)
            
            if response.status_code != 200:
                print(f"Error fetching moderated subreddits: {response.status_code} - {response.text}")
                return []
            
            data = response.json()
            moderated_subs = []
            
            for subreddit_data in data.get('data', {}).get('children', []):
                sub = subreddit_data.get('data', {})
                moderated_subs.append({
                    'name': sub.get('display_name', ''),
                    'title': sub.get('title', ''),
                    'subscribers': sub.get('subscribers', 0)
                })
            
            # Sort by subscriber count (largest first)
            moderated_subs.sort(key=lambda x: x['subscribers'], reverse=True)
            
            # Cache the results
            self.subreddit_cache = moderated_subs
            self.cache_timestamp = current_time
            
            return moderated_subs
            
        except Exception as e:
            print(f"Error fetching moderated subreddits: {e}")
            return []
    
    def analyze_with_ai(self, title, content, author, score, subreddit_name):
        """Use OpenAI to analyze content."""
        try:
            post_text = f"Title: {title}"
            if content and content.strip():
                post_text += f"\nContent: {content}"
            
            # Customize prompt based on subreddit
            subreddit_configs = {
                'grillsgonewild': {
                    'context': "r/grillsgonewild, a subreddit about BBQ grills and grilling equipment",
                    'rules': """- Spam or promotional content (especially affiliate links, discount codes)
- Off-topic content (not about grills/grilling/BBQ)
- Self-promotion without community engagement
- Low-effort posts
- Legitimate grilling content should be approved"""
                },
                'complainaboutanything': {
                    'context': "r/complainaboutanything, a subreddit where people can complain about anything",
                    'rules': """- REMOVE: Hate speech or harassment targeting individuals
- REMOVE: Personal attacks or doxxing
- REMOVE: Spam or promotional content
- REMOVE: Threats or incitement to violence
- REMOVE: Content promoting illegal activities
- APPROVE: Complaints and venting are generally allowed, even if heated
- APPROVE: Political complaints and criticism
- APPROVE: Personal frustrations and rants"""
                }
            }
            
            # Get subreddit-specific config or use default
            if subreddit_name in subreddit_configs:
                config = subreddit_configs[subreddit_name]
                context = config['context']
                rules = config['rules']
            else:
                context = f"r/{subreddit_name}, a Reddit community"
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

            response = self.openai_client.chat.completions.create(
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
            return {"action": "APPROVE", "reason": f"Error in analysis: {e}", "confidence": 1}
    
    def moderate_subreddit(self, subreddit_name, limit=5, human_review=False):
        """Moderate posts in a subreddit."""
        import time
        start_time = time.time()
        
        try:
            print(f"[PERF] Starting moderation for r/{subreddit_name} at {time.time()}")
            
            # Check if we have OAuth token from session
            if not hasattr(self, 'reddit_token') or not self.reddit_token:
                from flask import session
                self.reddit_token = session.get('reddit_token')
                if not self.reddit_token:
                    socketio.emit('error', {'message': 'No Reddit authentication token found. Please login again.'})
                    return
            
            self.current_subreddit = subreddit_name
            
            # Emit status update
            socketio.emit('status_update', {
                'message': f"Checking mod queue for r/{subreddit_name}...",
                'type': 'info'
            })
            
            # Use direct API call with timeout instead of PRAW
            headers = {
                'Authorization': f'Bearer {self.reddit_token}',
                'User-Agent': 'reddit-moderator-bot/2.0'
            }
            
            print(f"[PERF] Making API request to mod queue at {time.time()}")
            
            # Get items from mod queue with timeout
            import requests
            response = requests.get(
                f'https://oauth.reddit.com/r/{subreddit_name}/about/modqueue',
                headers=headers,
                params={'limit': limit},
                timeout=30  # 30 second timeout
            )
            
            api_time = time.time()
            print(f"[PERF] API request completed in {api_time - start_time:.2f} seconds")
            
            if response.status_code != 200:
                error_msg = f"Reddit API error: {response.status_code} - {response.text}"
                print(f"[ERROR] {error_msg}")
                socketio.emit('error', {'message': error_msg})
                return
            
            data = response.json()
            mod_queue_items = data.get('data', {}).get('children', [])
            
            if not mod_queue_items:
                socketio.emit('status_update', {
                    'message': "Mod queue is empty!",
                    'type': 'info'
                })
                print(f"[PERF] Total execution time: {time.time() - start_time:.2f} seconds")
                return
            
            socketio.emit('status_update', {
                'message': f"Found {len(mod_queue_items)} items in mod queue",
                'type': 'success'
            })
            
            print(f"[PERF] Processing {len(mod_queue_items)} items")
            
            for i, item_data in enumerate(mod_queue_items, 1):
                item_start = time.time()
                print(f"[PERF] Processing item {i} at {item_start}")
                
                # Extract item data from API response
                item = item_data.get('data', {})
                item_type = "submission" if 'selftext' in item else "comment"
                author = item.get('author', '[deleted]')
                
                if item_type == "submission":
                    title = item.get('title', '')
                    content = item.get('selftext', '')
                    display_content = content if content else title
                else:
                    title = f"Comment on: {item.get('link_title', 'Unknown')[:50]}..."
                    content = item.get('body', '')
                    display_content = content[:100] + ('...' if len(content) > 100 else '')
                
                # Get mod reports and removal reasons
                reports = []
                user_reports = item.get('user_reports', [])
                mod_reports = item.get('mod_reports', [])
                
                try:
                    # Process user reports
                    for report in user_reports:
                        reports.append({
                            'type': 'user_report',
                            'reason': report[0] if report else 'No reason given',
                            'count': report[1] if len(report) > 1 else 1
                        })
                    
                    # Process mod reports  
                    for report in mod_reports:
                        reports.append({
                            'type': 'mod_report',
                            'reason': report[0] if report else 'No reason given',
                            'moderator': report[1] if len(report) > 1 else 'Unknown'
                        })
                    
                    # Check if item was previously removed
                    removal_reason = None
                    if item.get('removed'):
                        removal_reason = item.get('removal_reason') or "Previously removed (no reason given)"
                            
                except Exception as e:
                    print(f"[ERROR] Error getting reports: {e}")
                
                # Emit item being analyzed
                socketio.emit('item_analyzing', {
                    'item_number': i,
                    'total_items': len(mod_queue_items),
                    'type': item_type,
                    'title': title,
                    'author': author,
                    'score': item.get('score', 0),
                    'content': display_content,
                    'full_content': content,  # Send full content for "Read More"
                    'url': f"https://reddit.com{item.get('permalink', '')}",
                    'permalink': item.get('permalink', ''),
                    'reports': reports,
                    'user_reports': user_reports,
                    'mod_reports': mod_reports,
                    'removal_reason': removal_reason,
                    'created_utc': item.get('created_utc', 0)
                })
                
                # Analyze with AI
                ai_start = time.time()
                decision = self.analyze_with_ai(title, content, author, item.get('score', 0), subreddit_name)
                ai_time = time.time() - ai_start
                print(f"[PERF] AI analysis took {ai_time:.2f} seconds")
                
                # Emit AI decision
                socketio.emit('ai_decision', {
                    'item_number': i,
                    'action': decision['action'],
                    'reason': decision['reason'],
                    'confidence': decision['confidence']
                })
                
                # In human review mode, don't take action immediately
                if not human_review:
                    # Take action immediately
                    action_taken = False
                    error_message = None
                    
                    try:
                        if decision['action'] == 'APPROVE':
                            item.mod.approve()
                            action_taken = True
                        elif decision['action'] == 'REMOVE':
                            item.mod.remove()
                            action_taken = True
                        
                        time.sleep(2)  # Rate limiting
                        
                    except Exception as e:
                        error_message = str(e)
                    
                    # Emit action result
                    socketio.emit('action_result', {
                        'item_number': i,
                        'action': decision['action'],
                        'action_taken': action_taken,
                        'human_review': False,
                        'error': error_message
                    })
            
            socketio.emit('moderation_complete', {
                'message': f"Moderation complete for r/{subreddit_name}!",
                'total_processed': len(mod_queue_items)
            })
            
        except Exception as e:
            error_time = time.time()
            print(f"[ERROR] Error in moderation after {error_time - start_time:.2f} seconds: {e}")
            socketio.emit('error', {
                'message': f"Error moderating r/{subreddit_name}: {str(e)}"
            })
        finally:
            total_time = time.time() - start_time
            print(f"[PERF] Total moderation time: {total_time:.2f} seconds")
    
    def chat_with_ai(self, user_message, context):
        """Chat with AI about a specific moderation decision."""
        try:
            print(f"AI Chat - User message: {user_message}")
            print(f"AI Chat - Context: {context}")
            
            # Build context from the original post and AI decision
            post_info = f"Post by u/{context.get('author', 'unknown')}: {context.get('content', '')}"
            ai_decision = f"AI Decision: {context.get('action', '')} - {context.get('reason', '')}"
            
            prompt = f"""You are a Reddit moderation assistant. You previously analyzed this content:

{post_info}

{ai_decision}

The human moderator is asking: {user_message}

Please provide a helpful response about your moderation decision, the content, or any follow-up questions they have. Be conversational and explain your reasoning clearly."""

            print(f"AI Chat - Sending prompt to OpenAI...")
            
            if not self.openai_client:
                return "Error: OpenAI client not initialized"

            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful Reddit moderation assistant having a conversation with a human moderator."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            
            ai_response = response.choices[0].message.content
            print(f"AI Chat - Got response: {ai_response[:100]}...")
            return ai_response
            
        except Exception as e:
            error_msg = f"Error in AI chat: {e}"
            print(error_msg)
            return error_msg
    
    def generate_removal_reason(self, context):
        """Generate a removal reason explanation for content."""
        try:
            author = context.get('author', 'unknown')
            content = context.get('content', '')
            title = context.get('title', '')
            item_type = context.get('type', 'post')
            user_reports = context.get('user_reports', [])
            mod_reports = context.get('mod_reports', [])
            ai_decision = f"AI recommended: {context.get('action', '')} - {context.get('reason', '')}"
            subreddit = context.get('subreddit', 'this subreddit')
            
            # Build complaint context
            complaint_context = ""
            if user_reports:
                complaint_context += f"\nUser reports: {', '.join([report[0] for report in user_reports])}"
            if mod_reports:
                complaint_context += f"\nMod reports: {', '.join([report[0] for report in mod_reports])}"
            
            post_info = f"{item_type.title()} by u/{author}"
            if title and title != content:
                post_info += f"\nTitle: {title}"
            if content:
                post_info += f"\nContent: {content}"
            
            prompt = f"""You are writing a removal reason for a Reddit {item_type}. Here's the full context:

{post_info}

{complaint_context}

{ai_decision}

Write a professional, clear removal reason that:
1. Explains why the content was removed
2. References the specific complaints/reports if relevant
3. Is respectful but firm
4. Helps the user understand what they did wrong

Keep it concise (2-3 sentences) and professional. This will be posted as the official removal reason."""

            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are writing professional Reddit removal reasons for moderators."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=200
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Content removed for violating subreddit rules. (Error generating detailed reason: {e})"

dashboard = ModerationDashboard()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/authenticate', methods=['POST'])
def authenticate():
    try:
        # Get credentials from request body
        credentials = request.get_json() if request.is_json else None
        
        success, message = dashboard.authenticate(credentials)
        
        response_data = {
            'success': success, 
            'message': message
        }
        
        # Include username if authentication was successful
        if success and dashboard.current_username:
            response_data['username'] = dashboard.current_username
            
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'Authentication error: {str(e)}'
        }), 500

# OAuth Routes
@app.route('/auth/reddit')
def reddit_oauth():
    """Redirect to Reddit OAuth authorization"""
    client_id = os.getenv('REDDIT_CLIENT_ID')
    
    # Check if environment variables are properly configured
    if not client_id:
        return redirect(url_for('index', error='missing_config', 
                               message='Reddit OAuth not configured. Please set REDDIT_CLIENT_ID in environment variables.'))
    
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state
    
    redirect_uri = request.url_root.rstrip('/') + '/auth/reddit/callback'
    
    params = {
        'client_id': client_id,
        'response_type': 'code',
        'state': state,
        'redirect_uri': redirect_uri,
        'duration': 'permanent',
        'scope': 'identity mysubreddits modposts read'
    }
    
    auth_url = 'https://www.reddit.com/api/v1/authorize?' + urllib.parse.urlencode(params)
    return redirect(auth_url)

@app.route('/auth/reddit/callback')
def reddit_callback():
    """Handle Reddit OAuth callback"""
    try:
        # Verify state parameter
        if request.args.get('state') != session.get('oauth_state'):
            return redirect(url_for('index', error='oauth_error', 
                                   message='Invalid OAuth state parameter'))
        
        # Get authorization code
        code = request.args.get('code')
        if not code:
            return redirect(url_for('index', error='oauth_error', 
                                   message='No authorization code received from Reddit'))
        
        # Exchange code for access token
        client_id = os.getenv('REDDIT_CLIENT_ID')
        client_secret = os.getenv('REDDIT_CLIENT_SECRET')
        
        # Check if environment variables are configured
        if not client_id or not client_secret:
            return redirect(url_for('index', error='missing_config', 
                                   message='Reddit OAuth credentials not configured on server'))
        
        redirect_uri = request.url_root.rstrip('/') + '/auth/reddit/callback'
        
        auth_string = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        headers = {
            'Authorization': f'Basic {auth_string}',
            'User-Agent': 'web:reddit-moderation-dashboard:v1.0 (by /u/bigmur72)'
        }
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri
        }
        
        response = requests.post('https://www.reddit.com/api/v1/access_token', 
                               headers=headers, data=data, timeout=30)
        
        if response.status_code != 200:
            return jsonify({'error': f'Token exchange failed: {response.text}'}), 400
        
        token_data = response.json()
        access_token = token_data.get('access_token')
        refresh_token = token_data.get('refresh_token')
        
        if not access_token:
            return jsonify({'error': 'No access token received'}), 400
        
        # Get user info
        user_headers = {
            'Authorization': f'Bearer {access_token}',
            'User-Agent': 'web:reddit-moderation-dashboard:v1.0 (by /u/bigmur72)'
        }
        
        user_response = requests.get('https://oauth.reddit.com/api/v1/me', 
                                   headers=user_headers, timeout=30)
        
        if user_response.status_code == 200:
            user_data = user_response.json()
            username = user_data.get('name', 'unknown')
        else:
            username = 'unknown'
        
        # Store tokens in session
        session['reddit_access_token'] = access_token
        session['reddit_refresh_token'] = refresh_token
        session['reddit_username'] = username
        session['authenticated'] = True
        
        # Clear OAuth state
        session.pop('oauth_state', None)
        
        return redirect('/?auth=success')
        
    except Exception as e:
        return jsonify({'error': f'OAuth callback error: {str(e)}'}), 500

@app.route('/auth/logout')
def logout():
    """Clear session and logout"""
    session.clear()
    return redirect('/?auth=logout')

@app.route('/api/auth-status')
def auth_status():
    """Check if user is authenticated"""
    return jsonify({
        'authenticated': session.get('authenticated', False),
        'username': session.get('reddit_username', None)
    })

@app.route('/api/moderated-subreddits', methods=['GET'])
def get_moderated_subreddits():
    """Get moderated subreddits using session token"""
    if not session.get('authenticated'):
        return jsonify({'error': 'Not authenticated'}), 401
    
    access_token = session.get('reddit_access_token')
    username = session.get('reddit_username')
    
    if not access_token:
        return jsonify({'error': 'No access token'}), 401
    
    try:
        headers = {
            'Authorization': f'Bearer {access_token}',
            'User-Agent': f'web:reddit-moderation-dashboard:v1.0 (by /u/{username})'
        }
        
        response = requests.get('https://oauth.reddit.com/subreddits/mine/moderator', 
                              headers=headers, timeout=30)
        
        if response.status_code != 200:
            return jsonify({'error': f'Failed to fetch subreddits: {response.text}'}), 400
        
        data = response.json()
        moderated_subs = []
        
        for subreddit_data in data.get('data', {}).get('children', []):
            sub = subreddit_data.get('data', {})
            moderated_subs.append({
                'name': sub.get('display_name', ''),
                'title': sub.get('title', ''),
                'subscribers': sub.get('subscribers', 0)
            })
        
        # Sort by subscriber count (largest first)
        moderated_subs.sort(key=lambda x: x['subscribers'], reverse=True)
        
        return jsonify({'subreddits': moderated_subs})
        
    except Exception as e:
        return jsonify({'error': f'Error fetching subreddits: {str(e)}'}), 500

@socketio.on('start_moderation')
def handle_moderation(data):
    subreddit_name = data.get('subreddit', '').strip()
    limit = int(data.get('limit', 5))
    human_review = data.get('human_review', True)
    
    if not subreddit_name:
        emit('error', {'message': 'Please enter a subreddit name'})
        return
    
    if not dashboard.reddit:
        emit('error', {'message': 'Please authenticate first'})
        return
    
    # Run moderation in background thread
    thread = threading.Thread(
        target=dashboard.moderate_subreddit,
        args=(subreddit_name, limit, human_review)
    )
    thread.daemon = True
    thread.start()

@socketio.on('process_batch_actions')
def handle_process_batch_actions(data):
    """Process all batch actions."""
    try:
        actions = data.get('actions', {})
        subreddit_name = data.get('subreddit', '')
        dry_run = data.get('dry_run', True)
        
        dashboard = ModerationDashboard()
        if not dashboard.authenticate():
            socketio.emit('batch_process_error', {'error': 'Authentication failed'})
            return
        
        results = dashboard.process_batch_actions(actions, subreddit_name, dry_run)
        socketio.emit('batch_process_complete', results)
        
    except Exception as e:
        error_time = time.time()
        print(f"[ERROR] Error in moderation after {error_time - start_time:.2f} seconds: {e}")
        socketio.emit('error', {'message': f'Moderation failed: {str(e)}'})
    finally:
        total_time = time.time() - start_time
        print(f"[PERF] Total moderation time: {total_time:.2f} seconds")

@socketio.on('ai_chat')
def handle_ai_chat(data):
    """Handle AI chat conversation within review blocks."""
    try:
        print(f"AI Chat handler - Received data: {data}")
        item_number = data.get('item_number')
        user_message = data.get('message')
        context = data.get('context', {})  # Original post data and AI decision
        
        print(f"AI Chat handler - Processing item {item_number}, message: {user_message}")
        
        # Use the global dashboard instance instead of creating a new one
        response = dashboard.chat_with_ai(user_message, context)
        
        print(f"AI Chat handler - Got response, emitting to client...")
        socketio.emit('ai_chat_response', {
            'item_number': item_number,
            'response': response
        })
        
    except Exception as e:
        error_msg = f"Error in AI chat handler: {e}"
        print(error_msg)
        socketio.emit('ai_chat_error', {
            'item_number': data.get('item_number'),
            'error': str(e)
        })

@socketio.on('generate_removal_reason')
def handle_generate_removal_reason(data):
    """Generate AI removal reason for content."""
    try:
        context = data.get('context', {})
        item_number = data.get('item_number')
        
        print(f"Generating removal reason for item {item_number} with context: {context}")
        
        # Use the global dashboard instance instead of creating a new one
        removal_reason = dashboard.generate_removal_reason(context)
        
        print(f"Generated removal reason: {removal_reason}")
        
        socketio.emit('removal_reason_generated', {
            'item_number': item_number,
            'reason': removal_reason
        })
        
    except Exception as e:
        print(f"Error generating removal reason: {e}")
        socketio.emit('removal_reason_error', {
            'item_number': data.get('item_number'),
            'error': str(e)
        })

@socketio.on('process_batch_actions')
def handle_batch_processing(data):
    actions = data.get('actions', {})
    subreddit_name = dashboard.current_subreddit
    
    if not dashboard.reddit or not subreddit_name:
        emit('error', {'message': 'No active moderation session'})
        return
    
    try:
        subreddit = dashboard.reddit.subreddit(subreddit_name)
        mod_queue_items = list(subreddit.mod.modqueue(limit=20))
        
        processed_count = 0
        for item_number, action in actions.items():
            if action == 'skip':
                continue
                
            # Find the corresponding Reddit item
            item_index = int(item_number) - 1
            if item_index < len(mod_queue_items):
                item = mod_queue_items[item_index]
                
                try:
                    if action == 'approve':
                        item.mod.approve()
                    elif action == 'remove':
                        item.mod.remove()
                    
                    processed_count += 1
                    time.sleep(1)  # Rate limiting
                    
                    # Emit progress
                    socketio.emit('batch_progress', {
                        'item_number': item_number,
                        'action': action,
                        'success': True
                    })
                    
                except Exception as e:
                    socketio.emit('batch_progress', {
                        'item_number': item_number,
                        'action': action,
                        'success': False,
                        'error': str(e)
                    })
        
        socketio.emit('batch_complete', {
            'message': f'Processed {processed_count} actions successfully',
            'processed_count': processed_count
        })
        
    except Exception as e:
        emit('error', {'message': f'Batch processing error: {str(e)}'})

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8080))
    socketio.run(app, debug=False, host='0.0.0.0', port=port)
