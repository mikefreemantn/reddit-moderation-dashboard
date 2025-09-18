// Reddit Moderation Dashboard JavaScript
const socket = io();

// DOM elements
const redditOAuthBtn = document.getElementById('reddit-oauth-btn');
const authStatus = document.getElementById('auth-status');
const loginForm = document.getElementById('login-form');
const loggedInSection = document.getElementById('logged-in-section');
const currentUserEl = document.getElementById('current-user');
const logoutBtn = document.getElementById('logout-btn');
const startBtn = document.getElementById('start-btn');
const subredditSelect = document.getElementById('subreddit-select');
const subredditInput = document.getElementById('subreddit-input');
const customSubredditCheckbox = document.getElementById('custom-subreddit-checkbox');
const limitInput = document.getElementById('limit-input');
const humanReviewCheckbox = document.getElementById('human-review-checkbox');
const statusLog = document.getElementById('status-log');
const resultsContainer = document.getElementById('moderation-results');
const batchActions = document.getElementById('batch-actions');
const processActionsBtn = document.getElementById('process-actions-btn');
const approveCountEl = document.getElementById('approve-count');
const removeCountEl = document.getElementById('remove-count');
const skipCountEl = document.getElementById('skip-count');

// OAuth elements
const openaiSection = document.querySelector('.openai-section');
const openaiApiKeyInput = document.getElementById('openai-api-key');
const saveOpenaiBtn = document.getElementById('save-openai-btn');
const rememberOpenaiKeyCheckbox = document.getElementById('remember-openai-key');

// Check authentication status on page load
async function checkAuthStatus() {
    try {
        const response = await fetch('/api/auth-status');
        const data = await response.json();
        
        if (data.authenticated) {
            showLoggedInState(data.username);
            loadSubreddits();
        } else {
            showLoginState();
        }
        
        // Check for URL parameters (error messages from OAuth)
        const urlParams = new URLSearchParams(window.location.search);
        const error = urlParams.get('error');
        const message = urlParams.get('message');
        
        if (error && message) {
            showError(decodeURIComponent(message));
            // Clean up URL
            window.history.replaceState({}, document.title, window.location.pathname);
        }
    } catch (error) {
        console.error('Error checking auth status:', error);
        showLoginState();
    }
}

function showError(message) {
    const authStatus = document.getElementById('auth-status');
    authStatus.innerHTML = `<div class="alert alert-danger"><i class="fas fa-exclamation-triangle"></i> ${message}</div>`;
    authStatus.style.display = 'block';
}

function showLoginState() {
    loginForm.style.display = 'block';
    loggedInSection.style.display = 'none';
    startBtn.disabled = true;
    subredditSelect.disabled = true;
}

function showLoggedInState(username) {
    loginForm.style.display = 'none';
    loggedInSection.style.display = 'block';
    currentUserEl.textContent = username;
    startBtn.disabled = false;
    subredditSelect.disabled = false;
    
    // Show OpenAI section if not already configured
    const savedOpenAIKey = localStorage.getItem('openai_api_key');
    if (!savedOpenAIKey) {
        openaiSection.style.display = 'block';
    }
}

async function loadSubreddits() {
    try {
        const response = await fetch('/api/moderated-subreddits');
        const data = await response.json();
        
        if (data.error) {
            showStatus(`Error loading subreddits: ${data.error}`, 'error');
            return;
        }
        
        // Clear existing options
        subredditSelect.innerHTML = '<option value="">Select a subreddit...</option>';
        
        // Add subreddits to dropdown
        data.subreddits.forEach(sub => {
            const option = document.createElement('option');
            option.value = sub.name;
            option.textContent = `r/${sub.name} (${sub.subscribers.toLocaleString()} subscribers)`;
            subredditSelect.appendChild(option);
        });
        
        showStatus(`Loaded ${data.subreddits.length} moderated subreddits`, 'success');
    } catch (error) {
        console.error('Error loading subreddits:', error);
        showStatus('Error loading subreddits', 'error');
    }
}

// Event listeners
redditOAuthBtn.addEventListener('click', () => {
    window.location.href = '/auth/reddit';
});

logoutBtn.addEventListener('click', () => {
    window.location.href = '/auth/logout';
});

saveOpenaiBtn.addEventListener('click', () => {
    const apiKey = openaiApiKeyInput.value.trim();
    if (!apiKey) {
        showStatus('Please enter an OpenAI API key', 'error');
        return;
    }
    
    if (rememberOpenaiKeyCheckbox.checked) {
        localStorage.setItem('openai_api_key', apiKey);
    }
    
    openaiSection.style.display = 'none';
    showStatus('OpenAI API key saved', 'success');
});

// Load saved OpenAI key on page load
function loadSavedOpenAIKey() {
    const savedKey = localStorage.getItem('openai_api_key');
    if (savedKey) {
        openaiApiKeyInput.value = savedKey;
    }
}

// Handle URL parameters for auth status
function handleAuthParams() {
    const urlParams = new URLSearchParams(window.location.search);
    const authParam = urlParams.get('auth');
    
    if (authParam === 'success') {
        showStatus('Successfully logged in with Reddit!', 'success');
        // Remove the parameter from URL
        window.history.replaceState({}, document.title, window.location.pathname);
    } else if (authParam === 'logout') {
        showStatus('Successfully logged out', 'info');
        window.history.replaceState({}, document.title, window.location.pathname);
    }
}

// Stats elements
const totalProcessedEl = document.getElementById('total-processed');
const totalApprovedEl = document.getElementById('total-approved');
const totalRemovedEl = document.getElementById('total-removed');
const apiCallsEl = document.getElementById('api-calls');

// State
let stats = {
    processed: 0,
    approved: 0,
    removed: 0,
    apiCalls: 0
};

let pendingActions = new Map(); // Store item decisions for batch processing
let reviewCounts = {
    approve: 0,
    remove: 0,
    skip: 0
};

// Credential management

function loadSavedCredentials() {
    const saved = localStorage.getItem('openai_api_key');
    if (saved && openaiApiKeyInput) {
        openaiApiKeyInput.value = saved;
        if (rememberOpenaiKeyCheckbox) {
            rememberOpenaiKeyCheckbox.checked = true;
        }
    }
}

function clearCredentials() {
    if (openaiApiKeyInput) {
        openaiApiKeyInput.value = '';
    }
    localStorage.removeItem('openai_api_key');
    localStorage.removeItem('reddit_mod_credentials');
}

function validateOpenAIKey() {
    if (!openaiApiKeyInput || !openaiApiKeyInput.value.trim()) {
        return false;
    }
    return true;
}

// OAuth Authentication
redditOAuthBtn.addEventListener('click', () => {
    window.location.href = '/auth/reddit';
});

// Logout functionality
logoutBtn.addEventListener('click', () => {
    // Clear UI state
    loginForm.style.display = 'block';
    loggedInSection.style.display = 'none';
    authStatus.innerHTML = '';
    authStatus.className = 'status-message';
    startBtn.disabled = true;
    subredditSelect.disabled = true;
    subredditSelect.innerHTML = '<option value="">Select a subreddit...</option>';
    
    // Clear credentials
    clearCredentials();
    
    // Redirect to logout endpoint
    window.location.href = '/auth/logout';
});

// OpenAI key management
saveOpenaiBtn.addEventListener('click', () => {
    const apiKey = openaiApiKeyInput.value.trim();
    if (apiKey) {
        if (rememberOpenaiKeyCheckbox.checked) {
            localStorage.setItem('openai_api_key', apiKey);
        }
        showError('OpenAI API key saved successfully!');
    } else {
        showError('Please enter an OpenAI API key');
    }
});

// Load saved credentials and initialize page
document.addEventListener('DOMContentLoaded', function() {
    loadSavedCredentials();
    checkAuthStatus();
});

// Custom subreddit checkbox handler
customSubredditCheckbox.addEventListener('change', () => {
    if (customSubredditCheckbox.checked) {
        subredditInput.style.display = 'block';
        subredditSelect.disabled = true;
        subredditSelect.value = '';
    } else {
        subredditInput.style.display = 'none';
        subredditSelect.disabled = false;
        subredditInput.value = '';
    }
});

// Load moderated subreddits function
async function loadModeratedSubreddits() {
    try {
        const response = await fetch('/api/moderated-subreddits');
        const data = await response.json();
        
        // Clear existing options except the first one
        subredditSelect.innerHTML = '<option value="">Select a subreddit...</option>';
        
        // Add moderated subreddits to dropdown
        data.subreddits.forEach(sub => {
            const option = document.createElement('option');
            option.value = sub.name;
            option.textContent = `r/${sub.name} (${sub.subscribers.toLocaleString()} subscribers)`;
            subredditSelect.appendChild(option);
        });
        
        subredditSelect.disabled = false;
        
    } catch (error) {
        console.error('Error loading moderated subreddits:', error);
    }
}

// Start moderation
startBtn.addEventListener('click', () => {
    let subreddit;
    
    if (customSubredditCheckbox.checked) {
        subreddit = subredditInput.value.trim();
    } else {
        subreddit = subredditSelect.value.trim();
    }
    
    const limit = parseInt(limitInput.value);
    const humanReview = humanReviewCheckbox.checked;
    
    if (!subreddit) {
        alert('Please select or enter a subreddit name');
        return;
    }
    
    // Reset stats and UI
    resetStats();
    resetReview();
    statusLog.innerHTML = '';
    resultsContainer.innerHTML = '';
    batchActions.style.display = 'none';
    
    startBtn.disabled = true;
    startBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Running...';
    
    // Emit start moderation event
    socket.emit('start_moderation', {
        subreddit: subreddit,
        limit: limit,
        human_review: humanReview
    });
});

// Socket event handlers
socket.on('status_update', (data) => {
    addLogEntry(data.message, data.type);
});

socket.on('item_analyzing', (data) => {
    const itemDiv = displayModerationItem(data, data.item_number || Date.now());
    resultsContainer.appendChild(itemDiv);
    
    addLogEntry(`Analyzing ${data.type} by u/${data.author}...`, 'info');
});

socket.on('ai_decision', (data) => {
    const itemDiv = document.querySelector(`[data-item="${data.item_number}"]`);
    if (itemDiv) {
        updateItemWithDecision(itemDiv, data);
        stats.apiCalls++;
        updateStats();
    }
    
    addLogEntry(`AI Decision: ${data.action} (${data.confidence}/10 confidence)`, 
               data.action === 'APPROVE' ? 'success' : 'error');
});

socket.on('action_result', (data) => {
    const itemDiv = document.querySelector(`[data-item="${data.item_number}"]`);
    if (itemDiv) {
        updateItemWithResult(itemDiv, data);
        
        stats.processed++;
        if (data.action === 'APPROVE') {
            stats.approved++;
        } else if (data.action === 'REMOVE') {
            stats.removed++;
        }
        updateStats();
    }
    
    if (data.dry_run) {
        addLogEntry(`[DRY RUN] Would ${data.action.toLowerCase()} this item`, 'info');
    } else if (data.action_taken) {
        addLogEntry(`✅ ${data.action} action completed`, 'success');
    } else if (data.error) {
        addLogEntry(`❌ Error: ${data.error}`, 'error');
    }
});

socket.on('moderation_complete', (data) => {
    addLogEntry(data.message, 'success');
    startBtn.disabled = false;
    startBtn.innerHTML = '<i class="fas fa-play"></i> Start Moderation';
    
    // Show batch actions if in human review mode
    if (humanReviewCheckbox.checked) {
        batchActions.style.display = 'block';
    }
});

socket.on('error', (data) => {
    addLogEntry(`Error: ${data.message}`, 'error');
    startBtn.disabled = false;
    startBtn.innerHTML = '<i class="fas fa-play"></i> Start Moderation';
});

// Helper functions
function addLogEntry(message, type = 'info') {
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    
    const icon = type === 'success' ? 'check' : type === 'error' ? 'times' : 'info';
    entry.innerHTML = `<i class="fas fa-${icon}"></i> ${message}`;
    
    statusLog.appendChild(entry);
    statusLog.scrollTop = statusLog.scrollHeight;
}

function displayModerationItem(data, itemNumber) {
    const itemDiv = document.createElement('div');
    itemDiv.className = 'mod-item-card';
    itemDiv.id = `item-${itemNumber}`;
    itemDiv.setAttribute('data-item', itemNumber);
    
    // Store item data globally for context extraction
    if (!window.itemData) window.itemData = {};
    window.itemData[itemNumber] = data;
    
    // Format post age
    const postAge = formatPostAge(data.created_utc);
    
    // Format user reports
    let reportsHtml = '';
    if (data.user_reports && data.user_reports.length > 0) {
        reportsHtml += '<div class="reports-section">';
        reportsHtml += '<div class="reports-header"><i class="fas fa-flag"></i> User Reports</div>';
        data.user_reports.forEach(report => {
            reportsHtml += `<div class="user-report">${report[0]} <span class="report-count">(${report[1]})</span></div>`;
        });
        reportsHtml += '</div>';
    }
    
    // Format mod reports
    if (data.mod_reports && data.mod_reports.length > 0) {
        reportsHtml += '<div class="reports-section">';
        reportsHtml += '<div class="reports-header"><i class="fas fa-shield-alt"></i> Mod Reports</div>';
        data.mod_reports.forEach(report => {
            reportsHtml += `<div class="mod-report">${report[0]} <span class="report-author">by ${report[1]}</span></div>`;
        });
        reportsHtml += '</div>';
    }
    
    // Format removal reasons
    if (data.removal_reason && data.removal_reason.trim()) {
        reportsHtml += '<div class="reports-section">';
        reportsHtml += '<div class="reports-header"><i class="fas fa-exclamation-triangle"></i> Previous Removal</div>';
        reportsHtml += `<div class="removal-reason">${data.removal_reason}</div>`;
        reportsHtml += '</div>';
    }
    
    const contentPreview = data.content && data.content.length > 300 ? data.content.substring(0, 300) + '...' : data.content;
    const hasMoreContent = data.content && data.content.length > 300;
    
    itemDiv.innerHTML = `
        <div class="card-header">
            <div class="post-info">
                <h3 class="post-title"><a href="${data.url || '#'}" target="_blank">${data.title || data.content?.substring(0, 50) + '...' || 'Post'}</a></h3>
                <div class="post-meta">
                    <span class="author-badge">u/${data.author || 'unknown'}</span>
                    <span class="score-badge">↑ ${data.score || 0}</span>
                    <span class="time-badge">${postAge}</span>
                </div>
            </div>
            <div class="action-buttons-top">
                <button class="action-btn approve-btn" onclick="setHumanDecision(${itemNumber}, 'APPROVE')" title="Approve">
                    <i class="fas fa-check"></i>
                    <span class="btn-text">Approve</span>
                </button>
                <button class="action-btn remove-btn" onclick="setHumanDecision(${itemNumber}, 'REMOVE')" title="Remove">
                    <i class="fas fa-times"></i>
                    <span class="btn-text">Remove</span>
                </button>
                <button class="action-btn skip-btn" onclick="setHumanDecision(${itemNumber}, 'SKIP')" title="Skip">
                    <i class="fas fa-forward"></i>
                    <span class="btn-text">Skip</span>
                </button>
            </div>
        </div>
        
        ${reportsHtml}
        
        <div class="content-section">
            ${data.full_content && data.full_content !== data.title ? `
                <div class="content-preview" id="preview-${itemNumber}">${data.full_content && data.full_content.length > 300 ? data.full_content.substring(0, 300) + '...' : data.full_content}</div>
                ${data.full_content && data.full_content.length > 300 ? `
                    <div class="content-full" id="full-${itemNumber}" style="display: none;">${data.full_content}</div>
                    <button class="read-more-btn" onclick="toggleContent(${itemNumber})" id="toggle-${itemNumber}">
                        <i class="fas fa-chevron-down"></i> Read More
                    </button>
                ` : ''}
            ` : ''}
        </div>
        
        <div class="ai-decision" id="decision-${itemNumber}"></div>
        
        <div class="card-footer">
            <div class="footer-columns">
                <div class="chat-column">
                    <div class="ai-chat-section" id="chat-${itemNumber}">
                        <div class="chat-header">
                            <i class="fas fa-robot"></i>
                            <span>AI Assistant</span>
                            <button class="chat-toggle-btn" onclick="toggleAIChat(${itemNumber})">
                                <i class="fas fa-comments"></i>
                            </button>
                        </div>
                        <div class="chat-messages" id="chat-messages-${itemNumber}"></div>
                        <div class="chat-input-container">
                            <input type="text" class="chat-input" id="chat-input-${itemNumber}" 
                                   placeholder="Ask about this decision..." 
                                   onkeypress="handleChatKeyPress(event, ${itemNumber})">
                            <button class="chat-send-btn" onclick="sendChatMessage(${itemNumber})">
                                <i class="fas fa-paper-plane"></i>
                            </button>
                        </div>
                    </div>
                </div>
                
                <div class="removal-column">
                    <div class="removal-reason-section" id="removal-reason-${itemNumber}">
                        <div class="removal-header">
                            <i class="fas fa-edit"></i>
                            <span>Removal Reason</span>
                            <button class="removal-toggle-btn" onclick="toggleRemovalReason(${itemNumber})">
                                <i class="fas fa-pen"></i>
                            </button>
                        </div>
                        <div class="removal-content">
                            <textarea class="removal-reason-text" id="removal-text-${itemNumber}" 
                                      placeholder="AI will generate a removal reason..."></textarea>
                            <div class="removal-actions">
                                <button class="generate-reason-btn" onclick="generateRemovalReason(${itemNumber})">
                                    <i class="fas fa-robot"></i> Generate
                                </button>
                                <button class="confirm-removal-btn" onclick="confirmRemoval(${itemNumber})">
                                    <i class="fas fa-check"></i> Confirm
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    return itemDiv;
}

function formatPostAge(timestamp) {
    const now = new Date();
    const postDate = new Date(timestamp * 1000);
    const diffMs = now - postDate;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);
    
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
}

function toggleContent(itemNumber) {
    const preview = document.getElementById(`preview-${itemNumber}`);
    const fullContent = document.getElementById(`full-${itemNumber}`);
    const toggleBtn = document.getElementById(`toggle-${itemNumber}`);
    
    if (fullContent.style.display === 'none') {
        // Show full content
        preview.style.display = 'none';
        fullContent.style.display = 'block';
        toggleBtn.innerHTML = '<i class="fas fa-chevron-up"></i> Read Less';
    } else {
        // Show preview
        preview.style.display = 'block';
        fullContent.style.display = 'none';
        toggleBtn.innerHTML = '<i class="fas fa-chevron-down"></i> Read More';
    }
}

function toggleAIChat(itemNumber) {
    const chatSection = document.getElementById(`chat-${itemNumber}`);
    const chatMessages = chatSection.querySelector('.chat-messages');
    const chatInput = chatSection.querySelector('.chat-input-container');
    const toggleBtn = chatSection.querySelector('.chat-toggle-btn');
    
    const isExpanded = chatMessages.style.display !== 'none';
    
    if (isExpanded) {
        chatMessages.style.display = 'none';
        chatInput.style.display = 'none';
        toggleBtn.innerHTML = '<i class="fas fa-comments"></i>';
    } else {
        chatMessages.style.display = 'block';
        chatInput.style.display = 'flex';
        toggleBtn.innerHTML = '<i class="fas fa-chevron-up"></i>';
    }
}

function handleChatKeyPress(event, itemNumber) {
    if (event.key === 'Enter') {
        sendChatMessage(itemNumber);
    }
}

function sendChatMessage(itemNumber) {
    const input = document.getElementById(`chat-input-${itemNumber}`);
    const message = input.value.trim();
    
    if (!message) return;
    
    // Add user message to chat
    addChatMessage(itemNumber, message, 'user');
    input.value = '';
    
    // Get context from the item
    const itemDiv = document.querySelector(`[data-item="${itemNumber}"]`);
    const context = getItemContext(itemDiv);
    
    console.log('Sending AI chat message:', {
        item_number: itemNumber,
        message: message,
        context: context
    });
    
    // Send to AI
    socket.emit('ai_chat', {
        item_number: itemNumber,
        message: message,
        context: context
    });
    
    // Show loading message
    addChatMessage(itemNumber, 'AI is thinking...', 'ai', true);
}

function addChatMessage(itemNumber, message, sender, isLoading = false) {
    const messagesDiv = document.getElementById(`chat-messages-${itemNumber}`);
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${sender}-message ${isLoading ? 'loading' : ''}`;
    
    if (isLoading) {
        messageDiv.id = `loading-${itemNumber}`;
    }
    
    messageDiv.innerHTML = `
        <div class="message-content">${message}</div>
        <div class="message-time">${new Date().toLocaleTimeString()}</div>
    `;
    
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function generateRemovalReason(itemNumber) {
    const itemDiv = document.querySelector(`[data-item="${itemNumber}"]`);
    const context = getItemContext(itemDiv);
    
    socket.emit('generate_removal_reason', {
        item_number: itemNumber,
        context: context
    });
    
    // Show loading in textarea
    const textarea = document.getElementById(`removal-text-${itemNumber}`);
    textarea.value = 'Generating removal reason...';
    textarea.disabled = true;
}

function getItemContext(itemDiv) {
    const itemNumber = itemDiv.getAttribute('data-item');
    
    // Extract context from the item div
    const author = itemDiv.querySelector('.author-badge')?.textContent?.replace('u/', '') || 'unknown';
    const content = itemDiv.querySelector('.content-preview')?.textContent || itemDiv.querySelector('.content-full')?.textContent || '';
    const aiDecision = itemDiv.querySelector('.decision-badge')?.textContent || '';
    const aiReason = itemDiv.querySelector('.ai-decision span:not(.decision-badge)')?.textContent || '';
    
    // Get subreddit from the form or use a fallback
    const subredditInput = document.getElementById('subreddit-input');
    const subredditSelect = document.getElementById('subreddit-select');
    const currentSub = subredditInput?.value || subredditSelect?.value || 'unknown';
    
    console.log('Context extracted:', {
        author,
        content: content.substring(0, 50) + '...',
        action: aiDecision,
        reason: aiReason,
        subreddit: currentSub
    });
    
    return {
        author: author,
        title: itemDiv.querySelector('.post-title a')?.textContent || '',
        content: content,
        type: itemDiv.querySelector('.ai-decision')?.dataset?.type || 'submission',
        action: aiDecision,
        reason: aiReason,
        subreddit: currentSub,
        user_reports: window.itemData?.[itemNumber]?.user_reports || [],
        mod_reports: window.itemData?.[itemNumber]?.mod_reports || []
    };
}

function toggleRemovalReason(itemNumber) {
    const removalSection = document.getElementById(`removal-reason-${itemNumber}`);
    const removalContent = removalSection.querySelector('.removal-content');
    const toggleBtn = removalSection.querySelector('.removal-toggle-btn');
    
    const isExpanded = removalContent.style.display !== 'none';
    
    if (isExpanded) {
        removalContent.style.display = 'none';
        toggleBtn.innerHTML = '<i class="fas fa-pen"></i>';
    } else {
        removalContent.style.display = 'block';
        toggleBtn.innerHTML = '<i class="fas fa-chevron-up"></i>';
        // Auto-generate removal reason when opened
        generateRemovalReason(itemNumber);
    }
}

function confirmRemoval(itemNumber) {
    const textarea = document.getElementById(`removal-text-${itemNumber}`);
    const removalReason = textarea.value.trim();
    
    if (!removalReason) {
        alert('Please enter a removal reason');
        return;
    }
    
    // Set the action to REMOVE and store the removal reason
    setHumanDecision(itemNumber, 'REMOVE');
    
    // Store removal reason for batch processing
    if (!window.removalReasons) {
        window.removalReasons = {};
    }
    window.removalReasons[itemNumber] = removalReason;
    
    // Hide the removal reason section
    const removalSection = document.getElementById(`removal-reason-${itemNumber}`);
    removalSection.style.display = 'none';
    
    logStatus(`Item ${itemNumber} marked for removal with custom reason`, 'success');
}

function setHumanDecision(itemNumber, action) {
    // Store the human decision
    if (!window.humanDecisions) {
        window.humanDecisions = {};
    }
    window.humanDecisions[itemNumber] = action;

    // Show removal reason section if REMOVE is selected
    const removalSection = document.getElementById(`removal-reason-${itemNumber}`);
    if (action === 'REMOVE' && removalSection) {
        removalSection.style.display = 'block';
        // Auto-generate removal reason
        generateRemovalReason(itemNumber);
    } else if (removalSection) {
        removalSection.style.display = 'none';
    }

    // Update UI to show override
    const itemDiv = document.querySelector(`[data-item="${itemNumber}"]`);
    setItemAction(itemNumber, action.toLowerCase(), false);

    // Update batch summary
    updateBatchSummary();

    logStatus(`Item ${itemNumber} decision: ${action}`, 'info');
}

function updateItemWithDecision(itemDiv, data) {
    const decisionDiv = itemDiv.querySelector('.ai-decision');
    const itemNumber = itemDiv.getAttribute('data-item');
    
    // Store AI decision data for context
    decisionDiv.dataset.type = window.itemData[itemNumber]?.type || 'submission';
    
    decisionDiv.innerHTML = `
        <span class="decision-badge ${data.action.toLowerCase()}">${data.action}</span>
        <span>${data.reason}</span>
        <div class="confidence-bar">
            <div class="confidence-fill" style="width: ${data.confidence * 10}%"></div>
        </div>
        <span>${data.confidence}/10</span>
    `;
    
    // Show action buttons and footer if in review mode
    if (humanReviewCheckbox.checked) {
        const actionButtonsTop = itemDiv.querySelector('.action-buttons-top');
        const cardFooter = itemDiv.querySelector('.card-footer');
        
        if (actionButtonsTop) actionButtonsTop.style.display = 'flex';
        if (cardFooter) cardFooter.style.display = 'block';
        
        // Set default action based on AI decision
        setItemAction(itemNumber, data.action.toLowerCase(), true);
    }
}

function updateItemWithResult(itemDiv, data) {
    itemDiv.className = `result-item ${data.action.toLowerCase()}`;
    
    const resultDiv = document.createElement('div');
    resultDiv.className = `action-result ${data.dry_run ? 'dry-run' : data.action_taken ? 'success' : 'error'}`;
    
    if (data.dry_run) {
        resultDiv.innerHTML = `<i class="fas fa-eye"></i> [DRY RUN] Would ${data.action.toLowerCase()}`;
    } else if (data.action_taken) {
        resultDiv.innerHTML = `<i class="fas fa-check"></i> ${data.action} completed`;
    } else {
        resultDiv.innerHTML = `<i class="fas fa-times"></i> Error: ${data.error}`;
    }
    
    itemDiv.appendChild(resultDiv);
}

function resetStats() {
    stats = { processed: 0, approved: 0, removed: 0, apiCalls: 0 };
    updateStats();
}

function resetReview() {
    pendingActions.clear();
    reviewCounts = { approve: 0, remove: 0, skip: 0 };
    updateReviewCounts();
}

function handleActionClick(button) {
    const itemNumber = button.getAttribute('data-item');
    const action = button.getAttribute('data-action');
    
    // Remove active class from all buttons in this item
    const itemDiv = document.querySelector(`[data-item="${itemNumber}"]`);
    itemDiv.querySelectorAll('.action-btn').forEach(btn => btn.classList.remove('active'));
    
    // Add active class to clicked button
    button.classList.add('active');
    
    // Update pending actions and counts
    setItemAction(itemNumber, action, false);
    
    // Show override indicator
    showOverrideIndicator(itemDiv, action);
}

function setItemAction(itemNumber, action, isDefault = false) {
    const oldAction = pendingActions.get(itemNumber);
    
    // Update counts
    if (oldAction) {
        reviewCounts[oldAction]--;
    }
    reviewCounts[action]++;
    
    // Store new action
    pendingActions.set(itemNumber, action);
    
    // Update UI
    updateReviewCounts();
    
    if (!isDefault) {
        // Activate the button
        const itemDiv = document.querySelector(`[data-item="${itemNumber}"]`);
        const actionBtn = itemDiv.querySelector(`[data-action="${action}"]`);
        actionBtn.classList.add('active');
    }
}

function showOverrideIndicator(itemDiv, action) {
    // Remove existing override indicator
    const existingOverride = itemDiv.querySelector('.human-override');
    if (existingOverride) {
        existingOverride.remove();
    }
    
    // Add new override indicator
    const overrideDiv = document.createElement('div');
    overrideDiv.className = 'human-override';
    overrideDiv.innerHTML = `
        <div class="override-text">
            <i class="fas fa-user"></i> Human decision: ${action.toUpperCase()}
        </div>
    `;
    
    itemDiv.appendChild(overrideDiv);
}

function updateReviewCounts() {
    approveCountEl.textContent = `${reviewCounts.approve} to Approve`;
    removeCountEl.textContent = `${reviewCounts.remove} to Remove`;
    skipCountEl.textContent = `${reviewCounts.skip} to Skip`;
}

function updateStats() {
    totalProcessedEl.textContent = stats.processed;
    totalApprovedEl.textContent = stats.approved;
    totalRemovedEl.textContent = stats.removed;
    apiCallsEl.textContent = stats.apiCalls;
}

// Process Actions button handler
processActionsBtn.addEventListener('click', () => {
    if (pendingActions.size === 0) {
        alert('No actions to process');
        return;
    }
    
    processActionsBtn.disabled = true;
    processActionsBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
    
    // Convert Map to object for transmission
    const actionsObj = Object.fromEntries(pendingActions);
    
    socket.emit('process_batch_actions', {
        actions: actionsObj
    });
});

// Batch processing event handlers
socket.on('batch_progress', (data) => {
    const itemDiv = document.querySelector(`[data-item="${data.item_number}"]`);
    if (itemDiv) {
        const resultDiv = document.createElement('div');
        resultDiv.className = `action-result ${data.success ? 'success' : 'error'}`;
        
        if (data.success) {
            resultDiv.innerHTML = `<i class="fas fa-check"></i> ${data.action.toUpperCase()} completed`;
            itemDiv.className = `result-item ${data.action}`;
        } else {
            resultDiv.innerHTML = `<i class="fas fa-times"></i> Error: ${data.error}`;
        }
        
        itemDiv.appendChild(resultDiv);
    }
    
    addLogEntry(`${data.success ? '✅' : '❌'} Item ${data.item_number}: ${data.action}`, 
               data.success ? 'success' : 'error');
});

socket.on('batch_complete', (data) => {
    addLogEntry(data.message, 'success');
    processActionsBtn.disabled = false;
    processActionsBtn.innerHTML = '<i class="fas fa-cogs"></i> Process All Actions';
});

// AI Chat event handlers
socket.on('ai_chat_response', (data) => {
    console.log('Received AI chat response:', data);
    
    // Remove loading message
    const loadingMsg = document.getElementById(`loading-${data.item_number}`);
    if (loadingMsg) {
        loadingMsg.remove();
    }
    
    // Add AI response
    addChatMessage(data.item_number, data.response, 'ai');
});

socket.on('ai_chat_error', (data) => {
    console.log('Received AI chat error:', data);
    
    // Remove loading message
    const loadingMsg = document.getElementById(`loading-${data.item_number}`);
    if (loadingMsg) {
        loadingMsg.remove();
    }
    
    // Add error message
    addChatMessage(data.item_number, `Error: ${data.error}`, 'ai');
});

// Removal reason event handlers
socket.on('removal_reason_generated', (data) => {
    const textarea = document.getElementById(`removal-text-${data.item_number}`);
    if (textarea) {
        textarea.value = data.reason;
        textarea.disabled = false;
    }
});

socket.on('removal_reason_error', (data) => {
    const textarea = document.getElementById(`removal-text-${data.item_number}`);
    if (textarea) {
        textarea.value = `Error generating reason: ${data.error}`;
        textarea.disabled = false;
    }
});

socket.on('batch_complete', (data) => {
    addLogEntry(data.message, 'success');
    processActionsBtn.disabled = false;
    processActionsBtn.innerHTML = '<i class="fas fa-cogs"></i> Process All Actions';
    
    // Update final stats
    stats.processed = data.processed_count;
    updateStats();
});

// Keyboard shortcuts for power users
let currentFocusedItem = null;

document.addEventListener('keydown', function(event) {
    // Only handle shortcuts when not typing in input fields
    if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
        return;
    }
    
    const humanReviewCheckbox = document.getElementById('human-review-checkbox');
    if (!humanReviewCheckbox || !humanReviewCheckbox.checked) {
        return; // Only work in human review mode
    }
    
    // Find the first visible mod item if none is focused
    if (!currentFocusedItem) {
        const firstItem = document.querySelector('.mod-item-card');
        if (firstItem) {
            setFocusedItem(firstItem);
        }
    }
    
    if (!currentFocusedItem) return;
    
    const itemNumber = parseInt(currentFocusedItem.id.replace('item-', ''));
    
    switch(event.key.toLowerCase()) {
        case 'a':
            event.preventDefault();
            setHumanDecision(itemNumber, 'APPROVE');
            moveToNextItem();
            showKeyboardHint('Approved');
            break;
        case 'r':
            event.preventDefault();
            setHumanDecision(itemNumber, 'REMOVE');
            moveToNextItem();
            showKeyboardHint('Marked for removal');
            break;
        case 's':
            event.preventDefault();
            setHumanDecision(itemNumber, 'SKIP');
            moveToNextItem();
            showKeyboardHint('Skipped');
            break;
        case 'arrowdown':
        case 'j':
            event.preventDefault();
            moveToNextItem();
            break;
        case 'arrowup':
        case 'k':
            event.preventDefault();
            moveToPreviousItem();
            break;
        case 'c':
            event.preventDefault();
            if (currentFocusedItem) {
                toggleAIChat(itemNumber);
                showKeyboardHint('Toggled AI chat');
            }
            break;
        case 'e':
            event.preventDefault();
            if (currentFocusedItem) {
                toggleRemovalReason(itemNumber);
                showKeyboardHint('Toggled removal reason');
            }
            break;
        case '?':
            event.preventDefault();
            showKeyboardShortcuts();
            break;
    }
});

function setFocusedItem(itemElement) {
    // Remove focus from previous item
    if (currentFocusedItem) {
        currentFocusedItem.classList.remove('keyboard-focused');
    }
    
    // Set new focused item
    currentFocusedItem = itemElement;
    if (currentFocusedItem) {
        currentFocusedItem.classList.add('keyboard-focused');
        currentFocusedItem.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

function moveToNextItem() {
    if (!currentFocusedItem) return;
    
    const nextItem = currentFocusedItem.nextElementSibling;
    if (nextItem && nextItem.classList.contains('mod-item-card')) {
        setFocusedItem(nextItem);
    }
}

function moveToPreviousItem() {
    if (!currentFocusedItem) return;
    
    const prevItem = currentFocusedItem.previousElementSibling;
    if (prevItem && prevItem.classList.contains('mod-item-card')) {
        setFocusedItem(prevItem);
    }
}

function showKeyboardHint(message) {
    // Create or update keyboard hint element
    let hint = document.getElementById('keyboard-hint');
    if (!hint) {
        hint = document.createElement('div');
        hint.id = 'keyboard-hint';
        hint.className = 'keyboard-hint';
        document.body.appendChild(hint);
    }
    
    hint.textContent = message;
    hint.classList.add('show');
    
    // Hide after 1.5 seconds
    setTimeout(() => {
        hint.classList.remove('show');
    }, 1500);
}

function showKeyboardShortcuts() {
    const shortcuts = `
        <div class="shortcuts-modal">
            <div class="shortcuts-content">
                <h3><i class="fas fa-keyboard"></i> Keyboard Shortcuts</h3>
                <div class="shortcuts-grid">
                    <div class="shortcut-group">
                        <h4>Actions</h4>
                        <div class="shortcut"><kbd>A</kbd> Approve</div>
                        <div class="shortcut"><kbd>R</kbd> Remove</div>
                        <div class="shortcut"><kbd>S</kbd> Skip</div>
                    </div>
                    <div class="shortcut-group">
                        <h4>Navigation</h4>
                        <div class="shortcut"><kbd>↓</kbd> or <kbd>J</kbd> Next item</div>
                        <div class="shortcut"><kbd>↑</kbd> or <kbd>K</kbd> Previous item</div>
                    </div>
                    <div class="shortcut-group">
                        <h4>Tools</h4>
                        <div class="shortcut"><kbd>C</kbd> Toggle AI chat</div>
                        <div class="shortcut"><kbd>E</kbd> Toggle removal reason</div>
                        <div class="shortcut"><kbd>?</kbd> Show shortcuts</div>
                    </div>
                </div>
                <button class="close-shortcuts" onclick="closeKeyboardShortcuts()">
                    <i class="fas fa-times"></i> Close
                </button>
            </div>
        </div>
    `;
    
    const modal = document.createElement('div');
    modal.id = 'shortcuts-modal';
    modal.innerHTML = shortcuts;
    document.body.appendChild(modal);
    
    // Close on click outside
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeKeyboardShortcuts();
        }
    });
    
    // Close on Escape key
    document.addEventListener('keydown', function escapeHandler(e) {
        if (e.key === 'Escape') {
            closeKeyboardShortcuts();
            document.removeEventListener('keydown', escapeHandler);
        }
    });
}

function closeKeyboardShortcuts() {
    const modal = document.getElementById('shortcuts-modal');
    if (modal) {
        modal.remove();
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    resetStats();
});
