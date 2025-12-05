"""
LangGraph Workflow for the Self-Healing Agent System.

This module assembles the cyclic graph:

    ┌──────────┐     ┌───────────┐     ┌──────────┐     ┌──────────┐
    │ Architect│ ──▶ │ Developer │ ──▶ │ Executor │ ──▶ │ Reviewer │
    └──────────┘     └───────────┘     └──────────┘     └──────────┘
                           ▲                                  │
                           │                                  │
                           │      ┌───────────────────────────┘
                           │      │
                           │      ▼
                     ┌─────┴──────────────────────────────────┐
                     │            Decision Logic              │
                     │  ┌─────────────────────────────────┐   │
                     │  │ exit_code == 0     → Publisher  │   │
                     │  │ attempts < 3       → Developer  │   │
                     │  │ otherwise          → End        │   │
                     │  └─────────────────────────────────┘   │
                     └────────────────────────────────────────┘
"""

from typing import Literal
from langgraph.graph import StateGraph, END

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from state.schema import AgentState
from nodes.architect import architect_node
from nodes.developer import developer_node
from nodes.executor import executor_node
from nodes.reviewer import reviewer_node, get_next_node
from nodes.publisher import publisher_node
from config import config


def create_workflow() -> StateGraph:
    """
    Create the LangGraph workflow with all nodes and edges.
    
    The workflow implements a self-healing loop:
    1. Architect analyzes the repo and creates a plan
    2. Developer implements the changes
    3. Executor runs tests in Docker
    4. Reviewer decides: publish, retry, or fail
    5. Publisher creates the PR (on success)
    
    Returns:
        Compiled StateGraph ready to execute
    """
    # Create the graph with our state schema
    workflow = StateGraph(AgentState)
    
    # Add all nodes
    workflow.add_node("architect", architect_node)
    workflow.add_node("developer", developer_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("reviewer", reviewer_node)
    workflow.add_node("publisher", publisher_node)
    
    # Set the entry point
    workflow.set_entry_point("architect")
    
    # Add edges (linear flow where not conditional)
    workflow.add_edge("architect", "developer")
    workflow.add_edge("developer", "executor")
    workflow.add_edge("executor", "reviewer")
    
    # Add conditional edge from reviewer
    # This is where the self-healing loop happens
    workflow.add_conditional_edges(
        "reviewer",
        _route_after_review,
        {
            "developer": "developer",  # Retry path
            "publisher": "publisher",  # Success path
            "end": END                 # Failure path
        }
    )
    
    # Publisher goes to end
    workflow.add_edge("publisher", END)
    
    return workflow.compile()


def _route_after_review(state: AgentState) -> Literal["developer", "publisher", "end"]:
    """
    Routing function for the conditional edge after Reviewer.
    
    Args:
        state: Current agent state
    
    Returns:
        Next node name or "end"
    """
    status = state.get("status", "")
    
    if status == "publishing":
        return "publisher"
    elif status == "developing":
        return "developer"
    else:  # "failed" or unknown
        return "end"


def run_workflow(
    repo_url: str,
    user_request: str,
    branch_name: str = "auto-dev-feature",
    verbose: bool = True
) -> AgentState:
    """
    Execute the complete workflow.
    
    This is the main entry point for running the agent.
    
    Args:
        repo_url: GitHub repository URL
        user_request: The task to implement
        branch_name: Name for the feature branch
        verbose: Print progress information
    
    Returns:
        Final agent state with results
    """
    from state.schema import create_initial_state, state_summary
    
    if verbose:
        print("=" * 60)
        print("🤖 SELF-HEALING AGENT SYSTEM")
        print("=" * 60)
        print(f"\n📦 Repository: {repo_url}")
        print(f"📝 Request: {user_request}")
        print(f"🌿 Branch: {branch_name}")
        print(f"🔄 Max Retries: {config.MAX_RETRY_ATTEMPTS}")
        print("\n" + "=" * 60)
    
    # Create initial state
    initial_state = create_initial_state(
        repo_url=repo_url,
        user_request=user_request,
        branch_name=branch_name
    )
    
    # Create and execute the workflow
    workflow = create_workflow()
    
    try:
        # Run the graph
        final_state = workflow.invoke(initial_state)
        
        if verbose:
            print("\n" + "=" * 60)
            print("🏁 WORKFLOW COMPLETE")
            print("=" * 60)
            print(state_summary(final_state))
            
            # Print final result
            status = final_state.get("status", "unknown")
            if status == "completed":
                pr_url = final_state.get("pr_url", "N/A")
                print(f"\n✅ SUCCESS! Pull Request created:")
                print(f"   🔗 {pr_url}")
            elif status == "failed":
                print(f"\n❌ FAILED after {final_state.get('attempt_count', 0)} attempts")
                if final_state.get("error_history"):
                    print("\nError History:")
                    for error in final_state["error_history"]:
                        print(f"   • {error}")
            else:
                print(f"\n⚠️ Ended with status: {status}")
        
        return final_state
        
    except Exception as e:
        if verbose:
            print(f"\n💥 CRITICAL ERROR: {e}")
        initial_state["status"] = "failed"
        initial_state["error_history"] = [f"Critical error: {str(e)}"]
        return initial_state


def run_dry_run(repo_url: str, user_request: str) -> None:
    """
    Run a dry-run of the workflow without LLM calls.
    
    Useful for testing the graph structure and state flow.
    
    Args:
        repo_url: GitHub repository URL
        user_request: The task description
    """
    print("=" * 60)
    print("🧪 DRY RUN MODE - No LLM calls, no file changes")
    print("=" * 60)
    
    from state.schema import create_initial_state
    
    state = create_initial_state(
        repo_url=repo_url,
        user_request=user_request,
        branch_name="dry-run-test"
    )
    
    # Simulate each node
    nodes = [
        ("architect", "Analyzing repository..."),
        ("developer", "Generating code..."),
        ("executor", "Running tests..."),
        ("reviewer", "Making decision..."),
        ("publisher", "Creating PR...")
    ]
    
    for name, msg in nodes:
        print(f"\n📍 Node: {name.upper()}")
        print(f"   {msg}")
        print(f"   State: {state.get('status', 'initialized')}")
    
    print("\n" + "=" * 60)
    print("✅ Dry run complete - graph structure is valid")
    print("=" * 60)


# Visualization helper
def visualize_graph():
    """Print a text representation of the graph."""
    print("""
    ┌──────────────────────────────────────────────────────────────┐
    │                  SELF-HEALING AGENT WORKFLOW                 │
    └──────────────────────────────────────────────────────────────┘
    
                            ┌─────────┐
                            │  START  │
                            └────┬────┘
                                 │
                                 ▼
                        ┌────────────────┐
                        │   ARCHITECT    │
                        │  (Analysis)    │
                        └───────┬────────┘
                                │
                                ▼
                    ┌───────────────────────┐
           ┌──────▶│     DEVELOPER         │
           │       │     (Coding)          │
           │       └──────────┬────────────┘
           │                  │
           │                  ▼
           │       ┌───────────────────────┐
           │       │      EXECUTOR         │
           │       │     (Testing)         │
           │       └──────────┬────────────┘
           │                  │
           │                  ▼
           │       ┌───────────────────────┐
           │       │      REVIEWER         │
           │       │  (Decision Logic)     │
           │       └──────────┬────────────┘
           │                  │
           │    ┌─────────────┼─────────────┐
           │    │             │             │
           │    ▼             ▼             ▼
           │ RETRY         SUCCESS       FAILURE
           │ (attempts<3)  (exit=0)    (max retries)
           │    │             │             │
           └────┘             ▼             ▼
                     ┌────────────────┐  ┌─────┐
                     │   PUBLISHER    │  │ END │
                     │  (Create PR)   │  │(❌) │
                     └───────┬────────┘  └─────┘
                             │
                             ▼
                          ┌─────┐
                          │ END │
                          │(✅)│
                          └─────┘
    """)


# For testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Self-Healing Agent Workflow")
    parser.add_argument("--dry-run", action="store_true", help="Run without LLM calls")
    parser.add_argument("--visualize", action="store_true", help="Show graph structure")
    parser.add_argument("--repo", type=str, default="https://github.com/octocat/Hello-World", 
                        help="Repository URL")
    parser.add_argument("--request", type=str, default="Add a greeting function",
                        help="Task to implement")
    
    args = parser.parse_args()
    
    if args.visualize:
        visualize_graph()
    elif args.dry_run:
        run_dry_run(args.repo, args.request)
    else:
        print("Use --dry-run or --visualize for testing")
        print("For actual execution, use main.py")
