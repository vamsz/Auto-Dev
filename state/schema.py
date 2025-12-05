"""
Global State Schema for the Self-Healing Agent System.

This is the "brain" that is passed between all agents in the LangGraph.
It maintains all context needed for the autonomous coding workflow.
"""

from typing import TypedDict, List, Optional, Literal


class AgentState(TypedDict, total=False):
    """
    The global state schema passed between all agent nodes.
    
    This represents the complete context of the autonomous coding task,
    allowing agents to share information and coordinate their work.
    
    Attributes:
        repo_url: The GitHub repository URL to work on
        branch_name: The feature branch name for changes
        user_request: The original user request/task description
        local_path: Local filesystem path where repo is cloned
        file_map: Complete list of all files in the repository
        relevant_files: Subset of files specifically needed for this task
        file_contents: Dict mapping file paths to their contents
        plan: Step-by-step implementation plan created by Architect
        current_step: Index of the current step being executed
        changes_made: List of changes made by Developer
        test_output: The most recent output from Docker test execution
        test_exit_code: Exit code from the last test run
        attempt_count: Number of retry attempts (max 3 to prevent infinite loops)
        error_history: History of errors encountered during retries
        status: Current overall status of the workflow
        pr_url: URL of the created Pull Request (after publishing)
        messages: Message history for LLM context
    """
    
    # Repository Information
    repo_url: str
    branch_name: str
    local_path: str
    
    # Task Information
    user_request: str
    
    # File Analysis (from Architect)
    file_map: List[str]
    relevant_files: List[str]
    file_contents: dict[str, str]
    
    # Implementation Plan (from Architect)
    plan: List[str]
    current_step: int
    
    # Development Progress (from Developer)
    changes_made: List[dict]  # [{file, change_type, description}]
    
    # Test Results (from Executor)
    test_output: str
    test_exit_code: int
    
    # Retry Management
    attempt_count: int
    error_history: List[str]
    
    # Workflow Status
    status: Literal["initialized", "analyzing", "developing", "testing", "publishing", "completed", "failed"]
    
    # Final Output
    pr_url: Optional[str]
    
    # LLM Message History
    messages: List[dict]


def create_initial_state(
    repo_url: str,
    user_request: str,
    branch_name: str = "auto-dev-feature"
) -> AgentState:
    """
    Create a new initial state for starting a workflow.
    
    Args:
        repo_url: GitHub repository URL
        user_request: The task description from the user
        branch_name: Name for the feature branch (default: auto-dev-feature)
    
    Returns:
        A fresh AgentState with initial values
    """
    return AgentState(
        repo_url=repo_url,
        branch_name=branch_name,
        local_path="",
        user_request=user_request,
        file_map=[],
        relevant_files=[],
        file_contents={},
        plan=[],
        current_step=0,
        changes_made=[],
        test_output="",
        test_exit_code=-1,
        attempt_count=0,
        error_history=[],
        status="initialized",
        pr_url=None,
        messages=[]
    )


def state_summary(state: AgentState) -> str:
    """
    Generate a human-readable summary of the current state.
    Useful for debugging and logging.
    """
    return f"""
=== Agent State Summary ===
Repository: {state.get('repo_url', 'N/A')}
Branch: {state.get('branch_name', 'N/A')}
Status: {state.get('status', 'N/A')}
Attempt: {state.get('attempt_count', 0)}/3

Files Analyzed: {len(state.get('file_map', []))}
Relevant Files: {len(state.get('relevant_files', []))}
Plan Steps: {len(state.get('plan', []))}
Current Step: {state.get('current_step', 0)}

Last Test Exit Code: {state.get('test_exit_code', 'N/A')}
Changes Made: {len(state.get('changes_made', []))}
Errors Encountered: {len(state.get('error_history', []))}
===========================
"""
