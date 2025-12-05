"""
Node E: The Publisher (Delivery)

The Publisher is responsible for:
1. Committing all changes with a meaningful message
2. Pushing the branch to the remote repository
3. Creating a Pull Request with the plan as description

This is the final node in the success path.
"""

from pathlib import Path
from typing import Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from state.schema import AgentState
from tools.github_tools import commit_changes, push_branch, push_pr, PRResult
from config import config


def publisher_node(state: AgentState) -> AgentState:
    """
    The Publisher node: Commits changes and creates a Pull Request.
    
    Input state:
        - local_path: Path to the cloned repository
        - branch_name: Feature branch name
        - plan: Implementation plan (used as PR description)
        - changes_made: List of changes for the commit message
        - user_request: Original request (for PR title)
    
    Output state updates:
        - pr_url: URL of the created PR
        - status: "publishing" -> "completed" or "failed"
    """
    print("\n📤 PUBLISHER: Creating Pull Request...")
    
    state = dict(state)  # Make mutable copy
    
    local_path = state.get("local_path")
    if not local_path:
        state["status"] = "failed"
        state["error_history"] = state.get("error_history", []) + [
            "Publisher: No local path in state"
        ]
        return state
    
    branch_name = state.get("branch_name", "auto-dev-feature")
    user_request = state.get("user_request", "Auto-generated changes")
    
    # Create PR title from user request
    pr_title = _create_pr_title(user_request)
    print(f"   PR Title: {pr_title}")
    
    # Create PR body from plan and changes
    pr_body = _create_pr_body(state)
    
    # Step 1: Commit all changes
    print("   Committing changes...")
    commit_message = _create_commit_message(state)
    
    success, commit_result = commit_changes(
        local_path=local_path,
        message=commit_message,
        add_all=True
    )
    
    if not success:
        if "No changes" in commit_result:
            print("   ⚠ No changes to commit")
        else:
            print(f"   ⚠ Commit issue: {commit_result}")
    else:
        print(f"   ✓ Committed: {commit_result}")
    
    # Step 2: Push branch
    print(f"   Pushing branch: {branch_name}...")
    push_success, push_msg = push_branch(
        local_path=local_path,
        branch_name=branch_name,
        force=False
    )
    
    if not push_success:
        print(f"   ✗ Push failed: {push_msg}")
        state["status"] = "failed"
        state["error_history"] = state.get("error_history", []) + [
            f"Push failed: {push_msg}"
        ]
        return state
    
    print(f"   ✓ Pushed: {push_msg}")
    
    # Step 3: Create Pull Request
    print("   Creating Pull Request...")
    pr_result: PRResult = push_pr(
        local_path=local_path,
        title=pr_title,
        body=pr_body,
        branch_name=branch_name,
        base_branch="main"  # Could be configurable
    )
    
    if pr_result.success:
        print(f"   ✓ {pr_result.message}")
        print(f"   🔗 {pr_result.pr_url}")
        state["pr_url"] = pr_result.pr_url
        state["status"] = "completed"
    else:
        print(f"   ✗ PR creation failed: {pr_result.message}")
        state["status"] = "failed"
        state["error_history"] = state.get("error_history", []) + [
            f"PR creation failed: {pr_result.message}"
        ]
    
    print("   ✓ Publishing phase complete!")
    return state


def _create_pr_title(user_request: str) -> str:
    """
    Create a PR title from the user request.
    
    Args:
        user_request: Original user request
    
    Returns:
        Formatted PR title (max 72 chars)
    """
    # Clean up the request
    title = user_request.strip()
    
    # Remove common prefixes
    prefixes_to_remove = [
        "please ", "can you ", "could you ", "i want to ", "i need to ",
        "implement ", "add ", "create ", "fix ", "update "
    ]
    
    title_lower = title.lower()
    for prefix in prefixes_to_remove:
        if title_lower.startswith(prefix):
            title = title[len(prefix):]
            break
    
    # Capitalize first letter
    if title:
        title = title[0].upper() + title[1:]
    
    # Add prefix
    title = f"[Auto-Dev] {title}"
    
    # Truncate if too long
    if len(title) > 72:
        title = title[:69] + "..."
    
    return title


def _create_commit_message(state: AgentState) -> str:
    """
    Create a commit message from the changes.
    
    Args:
        state: Current agent state
    
    Returns:
        Formatted commit message
    """
    user_request = state.get("user_request", "Auto-generated changes")
    changes_made = state.get("changes_made", [])
    
    # Title
    title = _create_pr_title(user_request).replace("[Auto-Dev] ", "")
    if len(title) > 50:
        title = title[:47] + "..."
    
    # Body with changes
    body_lines = [
        "",
        "Changes made by Auto-Dev Agent:",
        ""
    ]
    
    for change in changes_made[:10]:  # Limit to 10 changes
        action = change.get("action", "modify").upper()
        file = change.get("file", "unknown")
        desc = change.get("description", "")
        
        if desc:
            body_lines.append(f"  - [{action}] {file}: {desc[:50]}")
        else:
            body_lines.append(f"  - [{action}] {file}")
    
    if len(changes_made) > 10:
        body_lines.append(f"  ... and {len(changes_made) - 10} more changes")
    
    return title + "\n".join(body_lines)


def _create_pr_body(state: AgentState) -> str:
    """
    Create a detailed PR description.
    
    Args:
        state: Current agent state
    
    Returns:
        Formatted PR body in markdown
    """
    user_request = state.get("user_request", "No description provided")
    plan = state.get("plan", [])
    changes_made = state.get("changes_made", [])
    attempt_count = state.get("attempt_count", 0)
    
    body = f"""## 🤖 Auto-Generated Pull Request

This PR was created automatically by the Self-Healing Agent System.

### 📋 Original Request
{user_request}

### 🎯 Implementation Plan
"""
    
    for i, step in enumerate(plan, 1):
        body += f"{i}. {step}\n"
    
    body += "\n### 📝 Changes Made\n"
    
    for change in changes_made:
        action = change.get("action", "modify")
        file = change.get("file", "unknown")
        desc = change.get("description", "No description")
        
        emoji = {"create": "➕", "modify": "✏️", "delete": "🗑️"}.get(action, "📄")
        body += f"- {emoji} **{file}**: {desc}\n"
    
    body += f"""
### 🔄 Execution Summary
- **Attempts**: {attempt_count + 1}
- **Status**: ✅ All tests passed

---
*Generated by [Auto-Dev Agent](https://github.com/your-org/auto-dev)*
"""
    
    return body


def create_draft_pr(state: AgentState) -> AgentState:
    """
    Create a draft PR (for manual review before merging).
    
    Similar to publisher_node but creates a draft PR.
    
    Args:
        state: Current agent state
    
    Returns:
        Updated state
    """
    # For now, use the same logic
    # In the future, PyGithub supports draft=True parameter
    return publisher_node(state)


# For testing the node directly
if __name__ == "__main__":
    from state.schema import create_initial_state
    
    print("=== Publisher Node Test ===\n")
    
    # Test PR title generation
    test_requests = [
        "Add a new feature for user authentication",
        "Please implement a caching mechanism",
        "Fix the bug in the login page",
        "Update the README with installation instructions"
    ]
    
    print("PR Title Generation:")
    for req in test_requests:
        title = _create_pr_title(req)
        print(f"  '{req[:40]}...' → '{title}'")
    
    # Test commit message
    print("\nCommit Message Generation:")
    test_state = create_initial_state(
        repo_url="https://github.com/test/repo",
        user_request="Add fibonacci function"
    )
    test_state["changes_made"] = [
        {"action": "modify", "file": "main.py", "description": "Added fibonacci function"},
        {"action": "create", "file": "tests/test_fib.py", "description": "Added unit tests"}
    ]
    
    commit_msg = _create_commit_message(test_state)
    print(commit_msg)
    
    # Test PR body
    print("\n--- PR Body ---")
    test_state["plan"] = [
        "Add fibonacci function to main.py",
        "Create unit tests",
        "Update documentation"
    ]
    
    pr_body = _create_pr_body(test_state)
    print(pr_body[:500] + "...")
