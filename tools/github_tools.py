"""
GitHub Tools for the Self-Healing Agent System.

Provides Git and GitHub operations:
- clone_repo: Clone a repository locally
- checkout_branch: Create or switch branches
- push_pr: Push changes and create a Pull Request

Uses GitPython for local Git operations and PyGithub for API calls.
"""

import os
import re
import shutil
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass

from git import Repo, GitCommandError
from github import Github, GithubException

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import config


@dataclass
class CloneResult:
    """Result of cloning a repository."""
    success: bool
    local_path: str
    branch: str
    message: str
    
    def __str__(self) -> str:
        status = "✓" if self.success else "✗"
        return f"{status} {self.message}\n  Path: {self.local_path}\n  Branch: {self.branch}"


@dataclass
class PRResult:
    """Result of creating a Pull Request."""
    success: bool
    pr_url: Optional[str]
    pr_number: Optional[int]
    message: str
    
    def __str__(self) -> str:
        status = "✓" if self.success else "✗"
        if self.success:
            return f"{status} {self.message}\n  PR #{self.pr_number}: {self.pr_url}"
        return f"{status} {self.message}"


def parse_github_url(url: str) -> Tuple[str, str]:
    """
    Parse a GitHub URL to extract owner and repo name.
    
    Args:
        url: GitHub repository URL (HTTPS or SSH format, with or without token)
    
    Returns:
        Tuple of (owner, repo_name)
    
    Examples:
        >>> parse_github_url("https://github.com/owner/repo.git")
        ('owner', 'repo')
        >>> parse_github_url("git@github.com:owner/repo.git")
        ('owner', 'repo')
        >>> parse_github_url("https://token@github.com/owner/repo.git")
        ('owner', 'repo')
    """
    # First, strip any embedded token from the URL
    # Handle: https://TOKEN@github.com/owner/repo
    url_cleaned = re.sub(r'https://[^@]+@github\.com/', 'https://github.com/', url)
    
    # HTTPS format: https://github.com/owner/repo.git
    https_match = re.match(r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?$", url_cleaned)
    if https_match:
        return https_match.group(1), https_match.group(2)
    
    # SSH format: git@github.com:owner/repo.git
    ssh_match = re.match(r"git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$", url_cleaned)
    if ssh_match:
        return ssh_match.group(1), ssh_match.group(2)
    
    raise ValueError(f"Invalid GitHub URL format: {url_cleaned}")


def get_auth_url(url: str, token: str) -> str:
    """
    Add authentication token to GitHub URL for cloning.
    
    Args:
        url: Original GitHub URL
        token: GitHub Personal Access Token
    
    Returns:
        URL with embedded token for authentication
    """
    # Only modify HTTPS URLs
    if url.startswith("https://github.com/"):
        return url.replace("https://github.com/", f"https://{token}@github.com/")
    return url


def clone_repo(
    url: str,
    local_path: Optional[str] = None,
    branch: Optional[str] = None,
    force: bool = False
) -> CloneResult:
    """
    Clone a GitHub repository to local filesystem.
    
    Args:
        url: GitHub repository URL
        local_path: Local path to clone to (default: ./workspace/repo_name)
        branch: Specific branch to clone (default: default branch)
        force: If True, remove existing directory before cloning
    
    Returns:
        CloneResult with status and details
    """
    try:
        owner, repo_name = parse_github_url(url)
    except ValueError as e:
        return CloneResult(
            success=False,
            local_path="",
            branch="",
            message=str(e)
        )
    
    # Determine local path
    if local_path is None:
        workspace = Path(config.WORK_DIR)
        workspace.mkdir(parents=True, exist_ok=True)
        local_path = str(workspace / repo_name)
    
    local_path = str(Path(local_path).resolve())
    
    # Handle existing directory
    if Path(local_path).exists():
        if force:
            shutil.rmtree(local_path)
        else:
            # Check if it's already the right repo
            try:
                existing_repo = Repo(local_path)
                existing_remote = existing_repo.remotes.origin.url
                if owner in existing_remote and repo_name in existing_remote:
                    # Same repo - just pull latest
                    existing_repo.remotes.origin.pull()
                    return CloneResult(
                        success=True,
                        local_path=local_path,
                        branch=existing_repo.active_branch.name,
                        message=f"Repository already exists, pulled latest changes"
                    )
            except Exception:
                pass
            
            return CloneResult(
                success=False,
                local_path=local_path,
                branch="",
                message=f"Directory already exists: {local_path}. Use force=True to overwrite."
            )
    
    # Clone the repository
    try:
        # Add token for authentication if available
        auth_url = get_auth_url(url, config.GITHUB_TOKEN) if config.GITHUB_TOKEN else url
        
        clone_kwargs = {"depth": 1}  # Shallow clone for speed
        if branch:
            clone_kwargs["branch"] = branch
        
        repo = Repo.clone_from(auth_url, local_path, **clone_kwargs)
        
        return CloneResult(
            success=True,
            local_path=local_path,
            branch=repo.active_branch.name,
            message=f"Successfully cloned {owner}/{repo_name}"
        )
        
    except GitCommandError as e:
        return CloneResult(
            success=False,
            local_path=local_path,
            branch="",
            message=f"Git clone failed: {e.stderr}"
        )


def checkout_branch(
    local_path: str,
    branch_name: str,
    create: bool = True
) -> Tuple[bool, str]:
    """
    Create or switch to a branch in a local repository.
    
    Args:
        local_path: Path to the local repository
        branch_name: Name of the branch
        create: If True, create the branch if it doesn't exist
    
    Returns:
        Tuple of (success, message)
    """
    try:
        repo = Repo(local_path)
    except Exception as e:
        return False, f"Not a valid Git repository: {e}"
    
    try:
        # Check if branch exists locally
        if branch_name in repo.heads:
            repo.heads[branch_name].checkout()
            return True, f"Switched to existing branch: {branch_name}"
        
        # Check if branch exists remotely
        remote_ref = f"origin/{branch_name}"
        if remote_ref in [ref.name for ref in repo.refs]:
            repo.create_head(branch_name, remote_ref).checkout()
            return True, f"Checked out remote branch: {branch_name}"
        
        # Create new branch
        if create:
            new_branch = repo.create_head(branch_name)
            new_branch.checkout()
            return True, f"Created and switched to new branch: {branch_name}"
        
        return False, f"Branch not found: {branch_name}"
        
    except GitCommandError as e:
        return False, f"Git error: {e.stderr}"


def commit_changes(
    local_path: str,
    message: str,
    add_all: bool = True
) -> Tuple[bool, str]:
    """
    Stage and commit changes in a repository.
    
    Args:
        local_path: Path to the local repository
        message: Commit message
        add_all: If True, stage all changes
    
    Returns:
        Tuple of (success, message/commit_hash)
    """
    try:
        repo = Repo(local_path)
    except Exception as e:
        return False, f"Not a valid Git repository: {e}"
    
    try:
        if add_all:
            repo.git.add(A=True)
        
        # Check if there are changes to commit
        if not repo.is_dirty() and not repo.untracked_files:
            return False, "No changes to commit"
        
        commit = repo.index.commit(message)
        return True, str(commit.hexsha)[:8]
        
    except GitCommandError as e:
        return False, f"Commit failed: {e.stderr}"


def push_branch(
    local_path: str,
    branch_name: str,
    force: bool = False
) -> Tuple[bool, str]:
    """
    Push a branch to the remote repository.
    
    Args:
        local_path: Path to the local repository
        branch_name: Branch to push
        force: Force push if True
    
    Returns:
        Tuple of (success, message)
    """
    try:
        repo = Repo(local_path)
    except Exception as e:
        return False, f"Not a valid Git repository: {e}"
    
    try:
        origin = repo.remotes.origin
        
        # Update remote URL with token for authentication
        if config.GITHUB_TOKEN:
            current_url = origin.url
            auth_url = get_auth_url(current_url, config.GITHUB_TOKEN)
            origin.set_url(auth_url)
        
        push_args = {"u": True}  # Set upstream
        if force:
            push_args["force"] = True
        
        origin.push(branch_name, **push_args)
        return True, f"Pushed {branch_name} to origin"
        
    except GitCommandError as e:
        return False, f"Push failed: {e.stderr}"


def push_pr(
    local_path: str,
    title: str,
    body: str,
    branch_name: Optional[str] = None,
    base_branch: str = "main"
) -> PRResult:
    """
    Commit, push changes, and create a Pull Request.
    
    This is the main function used by the Publisher node.
    
    Args:
        local_path: Path to the local repository
        title: PR title
        body: PR description (use the plan here)
        branch_name: Branch to create PR from (default: current branch)
        base_branch: Target branch for the PR
    
    Returns:
        PRResult with PR URL and details
    """
    try:
        repo = Repo(local_path)
        origin_url = repo.remotes.origin.url
        owner, repo_name = parse_github_url(origin_url)
    except Exception as e:
        return PRResult(
            success=False,
            pr_url=None,
            pr_number=None,
            message=f"Repository error: {e}"
        )
    
    if not branch_name:
        branch_name = repo.active_branch.name
    
    # Commit any pending changes
    commit_success, commit_msg = commit_changes(
        local_path,
        f"auto-dev: {title}"
    )
    
    if not commit_success and "No changes" not in commit_msg:
        return PRResult(
            success=False,
            pr_url=None,
            pr_number=None,
            message=f"Commit failed: {commit_msg}"
        )
    
    # Push the branch
    push_success, push_msg = push_branch(local_path, branch_name)
    if not push_success:
        return PRResult(
            success=False,
            pr_url=None,
            pr_number=None,
            message=f"Push failed: {push_msg}"
        )
    
    # Create Pull Request via GitHub API
    if not config.GITHUB_TOKEN:
        return PRResult(
            success=False,
            pr_url=None,
            pr_number=None,
            message="GitHub token not configured. Cannot create PR."
        )
    
    try:
        g = Github(config.GITHUB_TOKEN)
        gh_repo = g.get_repo(f"{owner}/{repo_name}")
        
        # Check if PR already exists for this branch
        existing_prs = gh_repo.get_pulls(
            state="open",
            head=f"{owner}:{branch_name}",
            base=base_branch
        )
        
        for pr in existing_prs:
            # Update existing PR
            pr.edit(title=title, body=body)
            return PRResult(
                success=True,
                pr_url=pr.html_url,
                pr_number=pr.number,
                message=f"Updated existing PR #{pr.number}"
            )
        
        # Create new PR
        pr = gh_repo.create_pull(
            title=title,
            body=body,
            head=branch_name,
            base=base_branch
        )
        
        return PRResult(
            success=True,
            pr_url=pr.html_url,
            pr_number=pr.number,
            message=f"Created PR #{pr.number}"
        )
        
    except GithubException as e:
        return PRResult(
            success=False,
            pr_url=None,
            pr_number=None,
            message=f"GitHub API error: {e.data.get('message', str(e))}"
        )


def get_repo_info(url: str) -> dict:
    """
    Get information about a GitHub repository.
    
    Args:
        url: GitHub repository URL
    
    Returns:
        Dict with repository information
    """
    if not config.GITHUB_TOKEN:
        return {"error": "GitHub token not configured"}
    
    try:
        owner, repo_name = parse_github_url(url)
        g = Github(config.GITHUB_TOKEN)
        repo = g.get_repo(f"{owner}/{repo_name}")
        
        return {
            "name": repo.name,
            "full_name": repo.full_name,
            "description": repo.description,
            "default_branch": repo.default_branch,
            "language": repo.language,
            "stars": repo.stargazers_count,
            "open_issues": repo.open_issues_count,
            "url": repo.html_url,
        }
    except Exception as e:
        return {"error": str(e)}


# Test script
if __name__ == "__main__":
    print("=== GitHub Tools Test ===\n")
    
    # Test URL parsing
    test_urls = [
        "https://github.com/owner/repo.git",
        "https://github.com/owner/repo",
        "git@github.com:owner/repo.git",
    ]
    
    print("--- URL Parsing ---")
    for url in test_urls:
        try:
            owner, repo = parse_github_url(url)
            print(f"  {url} -> {owner}/{repo}")
        except ValueError as e:
            print(f"  {url} -> ERROR: {e}")
    
    # Check if token is configured
    print(f"\n--- Configuration ---")
    print(f"GitHub Token: {'✓ Configured' if config.GITHUB_TOKEN else '✗ Not configured'}")
    
    if config.GITHUB_TOKEN:
        # Test API access
        print("\n--- API Test ---")
        info = get_repo_info("https://github.com/python/cpython")
        if "error" not in info:
            print(f"  Repository: {info['full_name']}")
            print(f"  Language: {info['language']}")
            print(f"  Stars: {info['stars']}")
        else:
            print(f"  Error: {info['error']}")
    
    print("\n✓ Test completed!")
