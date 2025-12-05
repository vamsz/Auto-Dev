"""
Auto-Dev Web Interface

A simple web UI to control the Self-Healing Agent System.
Just run: python app.py
Then open: http://localhost:5000
"""

from flask import Flask, render_template_string, request, jsonify, Response
import threading
import queue
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import config
from state.schema import create_initial_state, state_summary
from graph.workflow import run_workflow

app = Flask(__name__)

# Queue for real-time logs
log_queue = queue.Queue()

# Store for current job status
current_job = {
    "running": False,
    "status": "idle",
    "result": None,
    "pr_url": None
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🤖 Auto-Dev Agent</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            color: #e4e4e4;
        }
        
        .container {
            max-width: 900px;
            margin: 0 auto;
            padding: 40px 20px;
        }
        
        header {
            text-align: center;
            margin-bottom: 40px;
        }
        
        h1 {
            font-size: 2.5rem;
            background: linear-gradient(90deg, #00d9ff, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }
        
        .subtitle {
            color: #888;
            font-size: 1.1rem;
        }
        
        .card {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 16px;
            padding: 30px;
            margin-bottom: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
            color: #00d9ff;
        }
        
        input[type="text"], textarea {
            width: 100%;
            padding: 14px 16px;
            border: 2px solid rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            background: rgba(0, 0, 0, 0.3);
            color: #fff;
            font-size: 1rem;
            transition: all 0.3s ease;
        }
        
        input[type="text"]:focus, textarea:focus {
            outline: none;
            border-color: #00d9ff;
            box-shadow: 0 0 20px rgba(0, 217, 255, 0.2);
        }
        
        textarea {
            min-height: 100px;
            resize: vertical;
        }
        
        .btn {
            padding: 14px 32px;
            border: none;
            border-radius: 10px;
            font-size: 1.1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            width: 100%;
        }
        
        .btn-primary {
            background: linear-gradient(90deg, #00d9ff, #00ff88);
            color: #1a1a2e;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(0, 217, 255, 0.3);
        }
        
        .btn-primary:disabled {
            background: #555;
            color: #999;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        
        .status-bar {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        
        .status-idle { background: rgba(100, 100, 100, 0.3); }
        .status-running { background: rgba(0, 217, 255, 0.2); }
        .status-success { background: rgba(0, 255, 136, 0.2); }
        .status-error { background: rgba(255, 100, 100, 0.2); }
        
        .spinner {
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255,255,255,0.3);
            border-top-color: #00d9ff;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .log-container {
            background: #0a0a15;
            border-radius: 10px;
            padding: 20px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 0.9rem;
            max-height: 400px;
            overflow-y: auto;
            line-height: 1.6;
        }
        
        .log-container::-webkit-scrollbar {
            width: 8px;
        }
        
        .log-container::-webkit-scrollbar-thumb {
            background: #333;
            border-radius: 4px;
        }
        
        .pr-link {
            display: inline-block;
            padding: 12px 24px;
            background: linear-gradient(90deg, #00ff88, #00d9ff);
            color: #1a1a2e;
            text-decoration: none;
            border-radius: 10px;
            font-weight: 600;
            margin-top: 15px;
            transition: all 0.3s ease;
        }
        
        .pr-link:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(0, 255, 136, 0.3);
        }
        
        .config-status {
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            margin-bottom: 20px;
        }
        
        .config-item {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.9rem;
        }
        
        .config-ok { color: #00ff88; }
        .config-missing { color: #ff6b6b; }
        
        .examples {
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid rgba(255,255,255,0.1);
        }
        
        .example-btn {
            padding: 8px 16px;
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 20px;
            color: #ddd;
            cursor: pointer;
            font-size: 0.85rem;
            margin: 5px;
            transition: all 0.2s;
        }
        
        .example-btn:hover {
            background: rgba(0, 217, 255, 0.2);
            border-color: #00d9ff;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🤖 Auto-Dev Agent</h1>
            <p class="subtitle">Self-Healing AI Coding Assistant</p>
        </header>
        
        <div class="card">
            <div class="config-status">
                <div class="config-item {{ 'config-ok' if groq_ok else 'config-missing' }}">
                    {{ '✓' if groq_ok else '✗' }} Groq API
                </div>
                <div class="config-item {{ 'config-ok' if github_ok else 'config-missing' }}">
                    {{ '✓' if github_ok else '✗' }} GitHub Token
                </div>
                <div class="config-item {{ 'config-ok' if docker_ok else 'config-missing' }}">
                    {{ '✓' if docker_ok else '⚠' }} Docker (optional)
                </div>
            </div>
            
            <form id="agentForm">
                <div class="form-group">
                    <label for="repo">📦 GitHub Repository URL</label>
                    <input type="text" id="repo" name="repo" 
                           placeholder="https://github.com/username/repository"
                           value="{{ default_repo }}">
                </div>
                
                <div class="form-group">
                    <label for="request">📝 What should I do?</label>
                    <textarea id="request" name="request" 
                              placeholder="Describe the task in natural language...&#10;Example: Add a login function with email validation"></textarea>
                </div>
                
                <div class="form-group">
                    <label for="branch">🌿 Branch Name (optional)</label>
                    <input type="text" id="branch" name="branch" 
                           placeholder="auto-dev-feature" value="auto-dev-feature">
                </div>
                
                <button type="submit" class="btn btn-primary" id="submitBtn">
                    🚀 Run Agent
                </button>
            </form>
            
            <div class="examples">
                <small style="color: #666;">Quick examples:</small><br>
                <button class="example-btn" onclick="setExample('Add error handling to all API endpoints')">Add error handling</button>
                <button class="example-btn" onclick="setExample('Create unit tests for the main functions')">Add unit tests</button>
                <button class="example-btn" onclick="setExample('Add logging throughout the application')">Add logging</button>
                <button class="example-btn" onclick="setExample('Refactor to use async/await pattern')">Async refactor</button>
            </div>
        </div>
        
        <div class="card">
            <div id="statusBar" class="status-bar status-idle">
                <span id="statusIcon">⏸️</span>
                <span id="statusText">Ready to start</span>
            </div>
            
            <div id="prResult" style="display: none; text-align: center;">
                <span style="font-size: 1.2rem;">✅ Pull Request Created!</span>
                <br>
                <a id="prLink" href="#" target="_blank" class="pr-link">View on GitHub →</a>
            </div>
            
            <div class="log-container" id="logContainer">
                <div style="color: #666;">Logs will appear here when you run the agent...</div>
            </div>
        </div>
    </div>
    
    <script>
        function setExample(text) {
            document.getElementById('request').value = text;
        }
        
        document.getElementById('agentForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const repo = document.getElementById('repo').value;
            const request = document.getElementById('request').value;
            const branch = document.getElementById('branch').value;
            
            if (!repo || !request) {
                alert('Please fill in the repository URL and task description');
                return;
            }
            
            // Update UI
            document.getElementById('submitBtn').disabled = true;
            document.getElementById('submitBtn').textContent = '⏳ Running...';
            document.getElementById('statusBar').className = 'status-bar status-running';
            document.getElementById('statusIcon').innerHTML = '<div class="spinner"></div>';
            document.getElementById('statusText').textContent = 'Agent is working...';
            document.getElementById('logContainer').innerHTML = '';
            document.getElementById('prResult').style.display = 'none';
            
            try {
                const response = await fetch('/run', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({repo, request, branch})
                });
                
                const result = await response.json();
                
                // Start polling for logs
                pollLogs();
                
            } catch (error) {
                showError('Failed to start agent: ' + error.message);
            }
        });
        
        async function pollLogs() {
            try {
                const response = await fetch('/status');
                const data = await response.json();
                
                // Update logs
                if (data.logs && data.logs.length > 0) {
                    const logContainer = document.getElementById('logContainer');
                    logContainer.innerHTML = data.logs.map(log => 
                        `<div>${log}</div>`
                    ).join('');
                    logContainer.scrollTop = logContainer.scrollHeight;
                }
                
                // Check if still running
                if (data.running) {
                    setTimeout(pollLogs, 500);
                } else {
                    // Finished
                    document.getElementById('submitBtn').disabled = false;
                    document.getElementById('submitBtn').textContent = '🚀 Run Agent';
                    
                    if (data.pr_url) {
                        document.getElementById('statusBar').className = 'status-bar status-success';
                        document.getElementById('statusIcon').textContent = '✅';
                        document.getElementById('statusText').textContent = 'Success! PR created.';
                        document.getElementById('prLink').href = data.pr_url;
                        document.getElementById('prResult').style.display = 'block';
                    } else if (data.status === 'failed') {
                        document.getElementById('statusBar').className = 'status-bar status-error';
                        document.getElementById('statusIcon').textContent = '❌';
                        document.getElementById('statusText').textContent = 'Failed. Check logs below.';
                    } else {
                        document.getElementById('statusBar').className = 'status-bar status-idle';
                        document.getElementById('statusIcon').textContent = '⏸️';
                        document.getElementById('statusText').textContent = 'Ready';
                    }
                }
            } catch (error) {
                console.error('Poll error:', error);
                setTimeout(pollLogs, 1000);
            }
        }
        
        function showError(message) {
            document.getElementById('submitBtn').disabled = false;
            document.getElementById('submitBtn').textContent = '🚀 Run Agent';
            document.getElementById('statusBar').className = 'status-bar status-error';
            document.getElementById('statusIcon').textContent = '❌';
            document.getElementById('statusText').textContent = message;
        }
    </script>
</body>
</html>
"""

# Store logs for the web UI
logs = []

class WebLogger:
    """Custom logger that captures output for the web UI."""
    def __init__(self):
        self.logs = []
        
    def write(self, message):
        if message.strip():
            self.logs.append(message.strip())
            # Also print to console
            sys.__stdout__.write(message)
            
    def flush(self):
        pass

web_logger = WebLogger()

@app.route('/')
def index():
    """Main page."""
    groq_ok = bool(config.GROQ_API_KEY)
    github_ok = bool(config.GITHUB_TOKEN)
    
    # Check Docker
    docker_ok = False
    try:
        from tools.docker_sandbox import DockerSandbox
        sandbox = DockerSandbox()
        docker_ok, _ = sandbox.check_docker_available()
        sandbox.cleanup()
    except:
        pass
    
    return render_template_string(
        HTML_TEMPLATE,
        groq_ok=groq_ok,
        github_ok=github_ok,
        docker_ok=docker_ok,
        default_repo=""
    )

@app.route('/run', methods=['POST'])
def run_agent():
    """Start the agent."""
    global current_job
    
    if current_job["running"]:
        return jsonify({"error": "Agent is already running"}), 400
    
    data = request.json
    repo = data.get('repo')
    task = data.get('request')
    branch = data.get('branch', 'auto-dev-feature')
    
    # Reset state
    current_job = {
        "running": True,
        "status": "starting",
        "result": None,
        "pr_url": None
    }
    web_logger.logs = []
    
    # Run in background thread
    def run_task():
        global current_job
        try:
            # Redirect stdout to capture logs
            old_stdout = sys.stdout
            sys.stdout = web_logger
            
            result = run_workflow(
                repo_url=repo,
                user_request=task,
                branch_name=branch,
                verbose=True
            )
            
            sys.stdout = old_stdout
            
            current_job["result"] = result
            current_job["status"] = result.get("status", "unknown")
            current_job["pr_url"] = result.get("pr_url")
            
        except Exception as e:
            current_job["status"] = "failed"
            web_logger.logs.append(f"❌ Error: {str(e)}")
        finally:
            current_job["running"] = False
    
    thread = threading.Thread(target=run_task)
    thread.start()
    
    return jsonify({"status": "started"})

@app.route('/status')
def get_status():
    """Get current status and logs."""
    return jsonify({
        "running": current_job["running"],
        "status": current_job["status"],
        "pr_url": current_job["pr_url"],
        "logs": web_logger.logs[-100:]  # Last 100 lines
    })


if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("🤖 Auto-Dev Web Interface")
    print("=" * 50)
    print("\n🌐 Open in your browser: http://localhost:5000\n")
    app.run(debug=False, port=5000, threaded=True)
