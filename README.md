# 🤖 Auto-Dev: Self-Healing AI Coding Agent

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Powered-green.svg)](https://langchain-ai.github.io/langgraph/)
[![Groq](https://img.shields.io/badge/Groq-LLaMA%203-orange.svg)](https://groq.com/)

An autonomous AI coding agent that analyzes GitHub repositories, implements code changes, tests them, and creates Pull Requests automatically. Features a **self-healing loop** that retries on failures.

![Auto-Dev Workflow](https://img.shields.io/badge/Workflow-Architect→Developer→Executor→Reviewer→Publisher-purple)

---

## ✨ Features

- 🧠 **AI-Powered Code Generation** - Uses Groq's LLaMA 3 (FREE) to write code
- 🔄 **Self-Healing Loop** - Automatically retries and fixes errors (up to 3 attempts)
- 🐳 **Docker Sandbox** - Runs tests in isolated containers for safety
- 🔗 **GitHub Integration** - Clones repos, commits changes, creates PRs automatically
- 🌐 **Web UI** - Beautiful browser interface (no command line needed!)
- 📝 **Natural Language** - Just describe what you want in plain English

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     SELF-HEALING AGENT WORKFLOW                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   START → [ARCHITECT] → [DEVELOPER] → [EXECUTOR] → [REVIEWER]  │
│               │              ↑             │            │       │
│               │              │             │            ▼       │
│               │              └─────────────┴──── RETRY (if fail)│
│               │                                         │       │
│               │                                         ▼       │
│               └──────────────────────────────→ [PUBLISHER] → PR │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Agent Nodes

| Node | Role | Description |
|------|------|-------------|
| 🏗️ **Architect** | Analysis | Clones repo, analyzes structure, creates implementation plan |
| 💻 **Developer** | Coding | Generates code based on plan, handles retries with error context |
| 🧪 **Executor** | Testing | Runs tests in Docker sandbox (syntax, pytest, linting) |
| 📋 **Reviewer** | Decision | Routes to retry, publish, or fail based on test results |
| 📤 **Publisher** | Delivery | Commits changes, pushes branch, creates Pull Request |

---

## 📋 Prerequisites

Before you begin, ensure you have:

- ✅ **Python 3.10+** - [Download](https://www.python.org/downloads/)
- ✅ **Git** - [Download](https://git-scm.com/downloads)
- ✅ **Docker Desktop** (optional but recommended) - [Download](https://www.docker.com/products/docker-desktop/)
- ✅ **Groq API Key** (FREE) - [Get yours](https://console.groq.com/keys)
- ✅ **GitHub Personal Access Token** - [Create one](https://github.com/settings/tokens)

---

## 🚀 Installation

### Step 1: Clone or Download

```bash
# Clone the repository
git clone https://github.com/yourusername/auto_dev.git
cd auto_dev

# Or if you already have it
cd c:\Users\vamsi\OneDrive\Desktop\auto_dev
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `langgraph` - Workflow orchestration
- `langchain-groq` - LLM integration
- `docker` - Container management
- `gitpython` - Git operations
- `PyGithub` - GitHub API
- `flask` - Web interface
- `python-dotenv` - Environment management

### Step 3: Configure API Keys

1. Copy the example environment file:
```bash
copy .env.example .env
```

2. Edit `.env` and add your keys:
```env
# Groq API (FREE - get at https://console.groq.com/keys)
GROQ_API_KEY=gsk_your_key_here

# Groq Model (options: llama-3.3-70b-versatile, llama-3.1-8b-instant, mixtral-8x7b-32768)
GROQ_MODEL=llama-3.3-70b-versatile

# GitHub Token (needs 'repo' scope - get at https://github.com/settings/tokens)
GITHUB_TOKEN=ghp_your_token_here

# Docker Configuration
DOCKER_IMAGE=python:3.10-slim
DOCKER_TIMEOUT=60

# Agent Configuration
MAX_RETRY_ATTEMPTS=3
WORK_DIR=./workspace
```

### Step 4: Get Your API Keys

#### Groq API Key (FREE):
1. Go to [https://console.groq.com/keys](https://console.groq.com/keys)
2. Sign up (no credit card required)
3. Click "Create API Key"
4. Copy and paste into `.env`

#### GitHub Token:
1. Go to [https://github.com/settings/tokens](https://github.com/settings/tokens)
2. Click "Generate new token (classic)"
3. Give it a name (e.g., "AutoDev")
4. Select scope: ✅ `repo` (full access)
5. Generate and copy to `.env`

### Step 5: Verify Installation

```bash
python main.py --check
```

You should see:
```
✓ Groq API Key: Set
✓ GitHub Token: Set
✓ Docker: Running (optional)
✅ Configuration is valid!
```

---

## 💻 Usage

### Option 1: Web Interface (Recommended)

The easiest way to use Auto-Dev:

```bash
python app.py
```

Then open your browser to: **http://localhost:5000**

You'll see a beautiful interface where you can:
1. Paste your GitHub repository URL
2. Describe what you want in plain English
3. Click "Run Agent"
4. Watch the live progress
5. Get a direct link to your Pull Request

### Option 2: Command Line

For automation and scripting:

```bash
# Basic usage
python main.py --repo https://github.com/owner/repo --request "Add a logging function"

# With custom branch name
python main.py --repo https://github.com/owner/repo --request "Fix the bug" --branch fix/my-bug

# Short form
python main.py -r https://github.com/owner/repo -t "Add docstrings"
```

### Option 3: Utility Commands

```bash
# Check configuration
python main.py --check

# Visualize the workflow
python main.py --visualize

# Dry run (test without making changes)
python main.py --dry-run
```

---

## 📖 Example Tasks

Here are some things you can ask Auto-Dev to do:

```bash
# Add a feature
python main.py -r https://github.com/user/repo -t "Add a greeting function that returns Hello World"

# Fix bugs
python main.py -r https://github.com/user/repo -t "Fix the null pointer exception in main.py"

# Add tests
python main.py -r https://github.com/user/repo -t "Create unit tests for the calculator module"

# Refactoring
python main.py -r https://github.com/user/repo -t "Refactor the API to use async/await"

# Documentation
python main.py -r https://github.com/user/repo -t "Add docstrings to all functions"

# Error handling
python main.py -r https://github.com/user/repo -t "Add error handling to all API endpoints"
```

---

## 📁 Project Structure

```
auto_dev/
├── 📄 app.py                    # Web UI (Flask)
├── 📄 main.py                   # CLI entry point
├── 📄 config.py                 # Configuration management
├── 📄 requirements.txt          # Dependencies
├── 📄 .env                      # Your API keys (create from .env.example)
├── 📄 .env.example              # Example environment file
├── 📄 .gitignore                # Git ignore rules
│
├── 📁 state/                    # State management
│   ├── __init__.py
│   └── schema.py                # AgentState TypedDict
│
├── 📁 tools/                    # Utility tools
│   ├── __init__.py
│   ├── file_tools.py            # File operations (read, write, list)
│   ├── docker_sandbox.py        # Docker container execution
│   └── github_tools.py          # Git/GitHub operations
│
├── 📁 nodes/                    # Agent nodes
│   ├── __init__.py
│   ├── architect.py             # Analysis & planning
│   ├── developer.py             # Code generation
│   ├── executor.py              # Test execution
│   ├── reviewer.py              # Decision routing
│   └── publisher.py             # PR creation
│
├── 📁 graph/                    # LangGraph workflow
│   ├── __init__.py
│   └── workflow.py              # Graph assembly
│
└── 📁 workspace/                # Cloned repositories (auto-created)
```

---

## ⚙️ Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | (required) | Your Groq API key |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | LLM model to use |
| `GITHUB_TOKEN` | (required) | GitHub Personal Access Token |
| `DOCKER_IMAGE` | `python:3.10-slim` | Docker image for testing |
| `DOCKER_TIMEOUT` | `60` | Container timeout (seconds) |
| `MAX_RETRY_ATTEMPTS` | `3` | Max self-healing retries |
| `WORK_DIR` | `./workspace` | Where repos are cloned |

### Available Groq Models

| Model | Best For | Context Window |
|-------|----------|----------------|
| `llama-3.3-70b-versatile` | Complex coding (recommended) | 128k tokens |
| `llama-3.1-8b-instant` | Fast, simple tasks | 128k tokens |
| `mixtral-8x7b-32768` | Good balance | 32k tokens |
| `gemma2-9b-it` | Alternative option | 8k tokens |

---

## 🔧 Troubleshooting

### Common Issues

#### 1. "GROQ_API_KEY not set"
```bash
# Make sure you have a .env file with your key
echo GROQ_API_KEY=gsk_your_key_here > .env
```

#### 2. "403 Forbidden" when pushing to GitHub
Your GitHub token doesn't have the right permissions:
1. Go to https://github.com/settings/tokens
2. Create a new **classic** token with `repo` scope
3. Update `.env` with the new token

#### 3. Docker credential errors
```
docker-credential-desktop not installed or not available in PATH
```
This is non-fatal. The agent will skip Docker tests and still create the PR.

To fix properly:
1. Open Docker Desktop → Settings
2. Or edit `~/.docker/config.json` and remove `credsStore`

#### 4. JSON parse errors
The LLM sometimes returns malformed JSON. The agent will:
1. Try to clean and reparse
2. If that fails, retry the request
3. After 3 attempts, report failure

#### 5. "No changes to commit"
This happens when:
- The Developer node failed to generate code
- Check the logs for JSON parse errors
- Try a simpler request

### Getting Help

If you encounter issues:
1. Run `python main.py --check` to verify configuration
2. Check the terminal logs for specific errors
3. Try a simpler request first (e.g., "Add a hello function")

---

## 🔒 Security Notes

- **API Keys**: Never commit your `.env` file (it's in `.gitignore`)
- **Docker Sandbox**: Code runs in isolated containers with:
  - No network access
  - Memory limits (512MB)
  - CPU limits (50%)
- **GitHub Token**: Use tokens with minimal required scope
- **Local Execution**: All processing happens on your machine

---

## 📊 How It Works

1. **You provide**: GitHub repo URL + natural language task
2. **Architect analyzes**: Clones repo, selects relevant files, creates plan
3. **Developer codes**: Generates code changes based on plan
4. **Executor tests**: Runs syntax check, pytest, linting in Docker
5. **Reviewer decides**:
   - ✅ Tests pass → Go to Publisher
   - ❌ Tests fail & retries < 3 → Back to Developer with error context
   - ❌ Tests fail & retries = 3 → Stop and report failure
6. **Publisher delivers**: Commits, pushes, creates Pull Request
7. **You receive**: Link to your PR on GitHub

---

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a Pull Request

---

## 📝 License

This project is open source. Feel free to use and modify as needed.

---

## 🙏 Acknowledgments

- [LangGraph](https://langchain-ai.github.io/langgraph/) - Workflow orchestration
- [Groq](https://groq.com/) - Fast, free LLM inference
- [LangChain](https://langchain.com/) - LLM framework

---

## 📞 Quick Reference

```bash
# Start Web UI
python app.py

# Check configuration
python main.py --check

# Run agent (CLI)
python main.py --repo URL --request "Your task"

# Visualize workflow
python main.py --visualize

# Dry run
python main.py --dry-run
```

**Web UI**: http://localhost:5000

---

Made with ❤️ by vamz
