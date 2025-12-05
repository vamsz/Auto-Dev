"""
Node D: The Reviewer (Decision Logic)

The Reviewer is a ROUTER, not an LLM agent.
It makes deterministic decisions based on the test results:

1. If Exit Code == 0 → Go to Publisher (success path)
2. If Exit Code != 0 AND attempts < 3 → Go to Developer (retry path)
3. If Exit Code != 0 AND attempts >= 3 → Stop and report (failure path)

This prevents infinite loops and ensures the system fails gracefully.
"""

from pathlib import Path
from typing import Literal

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from state.schema import AgentState
from config import config


# Routing outcomes
NextNode = Literal["developer", "publisher", "human_intervention"]


def reviewer_node(state: AgentState) -> AgentState:
    """
    The Reviewer node: Decides the next step based on test results.
    
    This is NOT an LLM node - it uses deterministic logic.
    
    Input state:
        - test_exit_code: Exit code from Executor
        - test_output: Output from Executor
        - attempt_count: Current retry count
    
    Output state updates:
        - attempt_count: Incremented if retrying
        - error_history: Updated with failure info
        - status: Updated based on decision
    
    Returns the state with routing info implicit in status.
    """
    print("\n📋 REVIEWER: Analyzing test results...")
    
    state = dict(state)  # Make mutable copy
    
    exit_code = state.get("test_exit_code", -1)
    attempt_count = state.get("attempt_count", 0)
    max_attempts = config.MAX_RETRY_ATTEMPTS
    
    print(f"   Exit Code: {exit_code}")
    print(f"   Attempt: {attempt_count + 1}/{max_attempts}")
    
    # Decision logic
    if exit_code == 0:
        # SUCCESS PATH
        print("   ✓ Decision: PUBLISH - Tests passed!")
        state["status"] = "publishing"
        # Don't increment attempt_count on success
        
    elif attempt_count < max_attempts - 1:  # -1 because we're about to increment
        # RETRY PATH
        print("   ↻ Decision: RETRY - Tests failed, attempting fix...")
        
        # Extract key error info for Developer
        test_output = state.get("test_output", "")
        error_summary = _extract_error_summary(test_output)
        
        # Add to error history for context
        state["error_history"] = state.get("error_history", []) + [
            f"Attempt {attempt_count + 1}: {error_summary}"
        ]
        
        # Increment attempt count
        state["attempt_count"] = attempt_count + 1
        state["status"] = "developing"  # Go back to Developer
        
        print(f"   Error: {error_summary[:80]}...")
        
    else:
        # FAILURE PATH - Max retries exceeded
        print("   ✗ Decision: HUMAN INTERVENTION - Max retries exceeded")
        
        state["error_history"] = state.get("error_history", []) + [
            f"Attempt {attempt_count + 1}: Max retries exceeded"
        ]
        state["attempt_count"] = attempt_count + 1
        state["status"] = "failed"
    
    print("   ✓ Review phase complete!")
    return state


def get_next_node(state: AgentState) -> NextNode:
    """
    Determine the next node based on current state.
    Used by LangGraph for conditional edges.
    
    Args:
        state: Current agent state
    
    Returns:
        Name of the next node to execute
    """
    status = state.get("status", "")
    
    if status == "publishing":
        return "publisher"
    elif status == "developing":
        return "developer"
    else:  # "failed" or unknown
        return "human_intervention"


def should_retry(state: AgentState) -> bool:
    """
    Check if the system should retry after a failure.
    
    Args:
        state: Current agent state
    
    Returns:
        True if should retry, False otherwise
    """
    exit_code = state.get("test_exit_code", -1)
    attempt_count = state.get("attempt_count", 0)
    
    return exit_code != 0 and attempt_count < config.MAX_RETRY_ATTEMPTS


def _extract_error_summary(test_output: str) -> str:
    """
    Extract a concise error summary from test output.
    
    This helps the Developer focus on the key issue.
    
    Args:
        test_output: Full test output from Executor
    
    Returns:
        Concise error summary
    """
    if not test_output:
        return "Unknown error (no output)"
    
    lines = test_output.split("\n")
    
    # Look for common error patterns
    error_lines = []
    
    for i, line in enumerate(lines):
        line_lower = line.lower()
        
        # Python exceptions
        if "error:" in line_lower or "exception:" in line_lower:
            error_lines.append(line.strip())
        
        # Assertion failures
        if "assertionerror" in line_lower or "assert" in line_lower and "failed" in line_lower:
            error_lines.append(line.strip())
        
        # Test failures
        if "failed" in line_lower and ("test" in line_lower or "::" in line):
            error_lines.append(line.strip())
        
        # Tracebacks (get the last few lines)
        if line.strip().startswith("E "):
            error_lines.append(line.strip())
    
    if error_lines:
        # Return first few unique errors
        unique_errors = list(dict.fromkeys(error_lines))[:3]
        return " | ".join(unique_errors)
    
    # Fallback: return last non-empty lines
    non_empty = [l.strip() for l in lines if l.strip()]
    if non_empty:
        return " | ".join(non_empty[-3:])
    
    return "Tests failed (see full output)"


def format_decision_report(state: AgentState) -> str:
    """
    Format a human-readable decision report.
    
    Args:
        state: Current agent state
    
    Returns:
        Formatted report string
    """
    status = state.get("status", "unknown")
    exit_code = state.get("test_exit_code", -1)
    attempts = state.get("attempt_count", 0)
    
    report = f"""
╔══════════════════════════════════════════════════════════════╗
║                    REVIEWER DECISION REPORT                  ║
╠══════════════════════════════════════════════════════════════╣
║  Test Exit Code: {exit_code:<43} ║
║  Attempt Number: {attempts}/{config.MAX_RETRY_ATTEMPTS:<41} ║
║  Decision: {status.upper():<49} ║
╚══════════════════════════════════════════════════════════════╝
"""
    
    if state.get("error_history"):
        report += "\nError History:\n"
        for error in state["error_history"][-5:]:
            report += f"  • {error[:60]}...\n" if len(error) > 60 else f"  • {error}\n"
    
    return report


# For testing the node directly
if __name__ == "__main__":
    from state.schema import create_initial_state, state_summary
    
    print("=== Reviewer Node Test ===\n")
    
    # Test Case 1: Success
    print("--- Test Case 1: Success ---")
    state1 = create_initial_state(
        repo_url="https://github.com/test/repo",
        user_request="Test request"
    )
    state1["test_exit_code"] = 0
    state1["test_output"] = "All tests passed!"
    state1["attempt_count"] = 0
    
    result1 = reviewer_node(state1)
    print(f"Status: {result1['status']}")
    print(f"Next: {get_next_node(result1)}")
    
    # Test Case 2: Failure with retries left
    print("\n--- Test Case 2: Failure (retries left) ---")
    state2 = create_initial_state(
        repo_url="https://github.com/test/repo",
        user_request="Test request"
    )
    state2["test_exit_code"] = 1
    state2["test_output"] = "AssertionError: Expected 5, got 3"
    state2["attempt_count"] = 1
    
    result2 = reviewer_node(state2)
    print(f"Status: {result2['status']}")
    print(f"Next: {get_next_node(result2)}")
    print(f"Attempts: {result2['attempt_count']}")
    
    # Test Case 3: Max retries exceeded
    print("\n--- Test Case 3: Max retries exceeded ---")
    state3 = create_initial_state(
        repo_url="https://github.com/test/repo",
        user_request="Test request"
    )
    state3["test_exit_code"] = 1
    state3["test_output"] = "Still failing"
    state3["attempt_count"] = 2  # Already at max - 1
    
    result3 = reviewer_node(state3)
    print(f"Status: {result3['status']}")
    print(f"Next: {get_next_node(result3)}")
    print(format_decision_report(result3))
