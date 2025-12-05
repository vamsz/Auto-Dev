#!/usr/bin/env python3
"""
Self-Healing Agent System - Main Entry Point

An autonomous coding agent that:
1. Analyzes GitHub repositories
2. Implements code changes based on natural language requests
3. Tests changes in a Docker sandbox
4. Self-heals by retrying on failures
5. Creates Pull Requests on success

Usage:
    python main.py --repo <github-url> --request "Your task description"
    python main.py --dry-run  # Test without LLM calls
    python main.py --check    # Verify configuration
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import config
from state.schema import create_initial_state, state_summary
from graph.workflow import run_workflow, run_dry_run, visualize_graph


def check_configuration() -> bool:
    """
    Verify all required configuration is present.
    
    Returns:
        True if configuration is valid, False otherwise
    """
    print("=" * 60)
    print("🔧 CONFIGURATION CHECK")
    print("=" * 60)
    
    config.print_status()
    
    missing = config.validate()
    if missing:
        print(f"\n❌ Missing required configuration:")
        for key in missing:
            print(f"   • {key}")
        print("\n💡 Create a .env file with the required values.")
        print("   See .env.example for reference.")
        return False
    
    # Check Docker
    print("\n--- Docker Check ---")
    try:
        from tools.docker_sandbox import DockerSandbox
        sandbox = DockerSandbox()
        available, message = sandbox.check_docker_available()
        sandbox.cleanup()
        
        if available:
            print(f"✓ {message}")
        else:
            print(f"⚠ {message}")
            print("   Docker is recommended but not required.")
    except Exception as e:
        print(f"⚠ Docker check failed: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Configuration is valid!")
    print("=" * 60)
    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Self-Healing Agent System - Autonomous Code Generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run the agent on a repository
  python main.py --repo https://github.com/owner/repo --request "Add a logging system"
  
  # Dry run (test graph without LLM calls)
  python main.py --dry-run
  
  # Check configuration
  python main.py --check
  
  # Visualize the workflow graph
  python main.py --visualize
        """
    )
    
    # Main arguments
    parser.add_argument(
        "--repo", "-r",
        type=str,
        help="GitHub repository URL to work on"
    )
    parser.add_argument(
        "--request", "-t",
        type=str,
        help="Natural language description of the task"
    )
    parser.add_argument(
        "--branch", "-b",
        type=str,
        default="auto-dev-feature",
        help="Branch name for changes (default: auto-dev-feature)"
    )
    
    # Mode flags
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check configuration and exit"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test graph flow without making changes"
    )
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Show workflow graph visualization"
    )
    parser.add_argument(
        "--quiet",
        dest="quiet",
        action="store_true",
        help="Reduce output verbosity"
    )
    
    args = parser.parse_args()
    
    # Handle mode flags
    if args.visualize:
        visualize_graph()
        return 0
    
    if args.check:
        success = check_configuration()
        return 0 if success else 1
    
    if args.dry_run:
        repo = args.repo or "https://github.com/octocat/Hello-World"
        request = args.request or "Add a sample feature"
        run_dry_run(repo, request)
        return 0
    
    # Validate required arguments for actual run
    if not args.repo:
        print("❌ Error: --repo is required")
        print("   Example: --repo https://github.com/owner/repo")
        return 1
    
    if not args.request:
        print("❌ Error: --request is required")
        print('   Example: --request "Add a caching layer"')
        return 1
    
    # Validate configuration
    missing = config.validate()
    if missing:
        print("❌ Configuration Error:")
        for key in missing:
            print(f"   Missing: {key}")
        print("\n💡 Run 'python main.py --check' for details")
        return 1
    
    # Run the workflow
    try:
        final_state = run_workflow(
            repo_url=args.repo,
            user_request=args.request,
            branch_name=args.branch,
            verbose=not args.quiet
        )
        
        # Return exit code based on result
        if final_state.get("status") == "completed":
            return 0
        else:
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
        return 130
    except Exception as e:
        print(f"\n💥 Critical Error: {e}")
        if not args.quiet:
            import traceback
            traceback.print_exc()
        return 1


def interactive_mode():
    """
    Run in interactive mode, prompting for inputs.
    """
    print("=" * 60)
    print("🤖 SELF-HEALING AGENT - Interactive Mode")
    print("=" * 60)
    
    # Check configuration first
    if not check_configuration():
        print("\n⚠️ Please fix configuration before continuing.")
        return
    
    print("\nEnter your request (or 'quit' to exit):\n")
    
    while True:
        try:
            repo = input("📦 Repository URL: ").strip()
            if repo.lower() in ("quit", "exit", "q"):
                break
            
            if not repo.startswith("http"):
                print("   Please enter a valid GitHub URL")
                continue
            
            request = input("📝 What should I do? ").strip()
            if not request:
                continue
            
            branch = input("🌿 Branch name [auto-dev-feature]: ").strip()
            if not branch:
                branch = "auto-dev-feature"
            
            print("\n")
            run_workflow(repo, request, branch)
            
            print("\n" + "-" * 40)
            continue_choice = input("Continue with another task? [y/N]: ").strip().lower()
            if continue_choice != "y":
                break
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except EOFError:
            break


if __name__ == "__main__":
    # Check if running interactively with no arguments
    if len(sys.argv) == 1:
        # Show help
        print(__doc__)
        print("\nQuick start:")
        print("  python main.py --check           # Verify setup")
        print("  python main.py --visualize       # See workflow diagram")
        print("  python main.py --dry-run         # Test without changes")
        print("  python main.py --repo URL -t 'task'  # Run the agent")
        sys.exit(0)
    
    sys.exit(main())
