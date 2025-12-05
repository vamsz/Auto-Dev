"""
Node A: The Architect (Analysis)

The Architect is responsible for:
1. Cloning the repository
2. Analyzing the file structure
3. Selecting relevant files for the task
4. Creating an implementation plan

This node does NOT read every file (to prevent token overflow).
It reads file names and structure to make intelligent decisions.
"""

import json
from pathlib import Path
from typing import List

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from state.schema import AgentState
from tools.file_tools import list_files, read_file
from tools.github_tools import clone_repo, checkout_branch
from config import config


ARCHITECT_SYSTEM_PROMPT = """You are a Senior Software Architect analyzing a codebase to plan a feature implementation.

Your responsibilities:
1. Understand the repository structure from the file list
2. Identify which files are relevant to the user's request
3. Create a step-by-step implementation plan

Guidelines:
- Select ONLY the files that are truly relevant (usually 3-10 files max)
- Consider dependencies: if modifying a function, you may need its callers/callees
- Look for existing patterns in the codebase to follow
- Plan should include creating/updating tests

Output your response as JSON with this exact structure:
{
    "relevant_files": ["path/to/file1.py", "path/to/file2.py"],
    "plan": [
        "Step 1: Description of first change",
        "Step 2: Description of second change",
        ...
    ],
    "reasoning": "Brief explanation of your analysis"
}

Be concise but thorough. The Developer will use your plan to implement changes."""


def get_llm():
    """Get configured Groq LLM instance (LLaMA 3)."""
    return ChatGroq(
        model=config.GROQ_MODEL,
        api_key=config.GROQ_API_KEY,
        temperature=0.1  # Low temperature for more consistent analysis
    )


def architect_node(state: AgentState) -> AgentState:
    """
    The Architect node: Analyzes the repository and creates an implementation plan.
    
    Input state:
        - repo_url: GitHub repository URL
        - user_request: The task description
        - branch_name: Branch to work on
    
    Output state updates:
        - local_path: Where the repo was cloned
        - file_map: Complete list of repository files
        - relevant_files: Files needed for the task
        - plan: Step-by-step implementation plan
        - status: "analyzing" -> "developing"
    """
    print("\n🏗️  ARCHITECT: Starting analysis...")
    
    # Update status
    state = dict(state)  # Make mutable copy
    state["status"] = "analyzing"
    
    # Step 1: Clone the repository
    print(f"   Cloning repository: {state['repo_url']}")
    clone_result = clone_repo(
        url=state["repo_url"],
        branch=None,  # Use default branch first
        force=False
    )
    
    if not clone_result.success:
        state["error_history"] = state.get("error_history", []) + [
            f"Clone failed: {clone_result.message}"
        ]
        state["status"] = "failed"
        return state
    
    state["local_path"] = clone_result.local_path
    print(f"   ✓ Cloned to: {clone_result.local_path}")
    
    # Step 2: Create feature branch
    branch_name = state.get("branch_name", "auto-dev-feature")
    success, msg = checkout_branch(
        local_path=state["local_path"],
        branch_name=branch_name,
        create=True
    )
    print(f"   ✓ Branch: {branch_name}")
    
    # Step 3: List all files in repository
    print("   Scanning repository structure...")
    try:
        all_files = list_files(
            state["local_path"],
            extensions=[".py", ".js", ".ts", ".jsx", ".tsx", ".json", ".yaml", ".yml", ".md", ".txt"],
            max_depth=5  # Don't go too deep
        )
        state["file_map"] = all_files
        print(f"   ✓ Found {len(all_files)} files")
    except Exception as e:
        state["error_history"] = state.get("error_history", []) + [
            f"File scan failed: {str(e)}"
        ]
        state["status"] = "failed"
        return state
    
    # Step 4: Use LLM to analyze and create plan
    print("   Analyzing with AI...")
    
    llm = get_llm()
    
    # Create file tree representation
    file_tree = "\n".join(f"  - {f}" for f in all_files[:100])  # Limit to 100 files
    if len(all_files) > 100:
        file_tree += f"\n  ... and {len(all_files) - 100} more files"
    
    # Read key files for context (README, main entry points)
    context_files = []
    key_files = ["README.md", "readme.md", "setup.py", "pyproject.toml", "package.json"]
    for key_file in key_files:
        matching = [f for f in all_files if f.lower().endswith(key_file.lower())]
        if matching:
            try:
                content = read_file(
                    str(Path(state["local_path"]) / matching[0]),
                    with_line_numbers=False
                )
                if len(content) < 3000:  # Only include if not too large
                    context_files.append(f"### {matching[0]}\n```\n{content}\n```")
            except:
                pass
    
    context_str = "\n\n".join(context_files[:3]) if context_files else "No README or config files found."
    
    user_message = f"""
## User Request
{state['user_request']}

## Repository Structure
{file_tree}

## Key Files Content
{context_str}

Analyze this repository and create a plan to implement the user's request.
Remember to output valid JSON with "relevant_files", "plan", and "reasoning" keys.
"""
    
    try:
        response = llm.invoke([
            SystemMessage(content=ARCHITECT_SYSTEM_PROMPT),
            HumanMessage(content=user_message)
        ])
        
        # Parse the response
        response_text = response.content
        
        # Try to extract JSON from response
        try:
            # Find JSON in response (might be wrapped in markdown)
            import re
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                analysis = json.loads(json_match.group())
            else:
                raise ValueError("No JSON found in response")
            
            state["relevant_files"] = analysis.get("relevant_files", [])
            state["plan"] = analysis.get("plan", [])
            
            print(f"   ✓ Identified {len(state['relevant_files'])} relevant files")
            print(f"   ✓ Created {len(state['plan'])}-step plan")
            
            # Log the reasoning
            if "reasoning" in analysis:
                print(f"   Analysis: {analysis['reasoning'][:100]}...")
                
        except json.JSONDecodeError as e:
            # Fallback: use heuristics if LLM didn't return valid JSON
            print(f"   ⚠ JSON parse failed, using fallback analysis")
            state["relevant_files"] = [f for f in all_files if f.endswith(".py")][:10]
            state["plan"] = [
                f"Analyze the codebase for: {state['user_request']}",
                "Implement the required changes",
                "Add or update tests",
                "Verify the implementation"
            ]
            
    except Exception as e:
        state["error_history"] = state.get("error_history", []) + [
            f"LLM analysis failed: {str(e)}"
        ]
        # Use fallback
        state["relevant_files"] = [f for f in all_files if f.endswith(".py")][:10]
        state["plan"] = [
            f"Implement: {state['user_request']}",
            "Add tests",
            "Verify"
        ]
    
    # Step 5: Read content of relevant files
    print("   Loading relevant file contents...")
    file_contents = {}
    for rel_path in state["relevant_files"][:15]:  # Limit to 15 files
        full_path = Path(state["local_path"]) / rel_path
        try:
            content = read_file(str(full_path), with_line_numbers=True)
            file_contents[rel_path] = content
        except Exception as e:
            print(f"   ⚠ Could not read {rel_path}: {e}")
    
    state["file_contents"] = file_contents
    state["current_step"] = 0
    state["status"] = "developing"
    
    print("   ✓ Architecture phase complete!")
    return state


# For testing the node directly
if __name__ == "__main__":
    from state.schema import create_initial_state, state_summary
    
    print("=== Architect Node Test ===\n")
    
    # Create test state
    test_state = create_initial_state(
        repo_url="https://github.com/octocat/Hello-World",
        user_request="Add a new greeting function that says 'Hello, World!' in different languages",
        branch_name="feature/multilingual-greeting"
    )
    
    print("Initial State:")
    print(state_summary(test_state))
    
    # Run the architect
    result_state = architect_node(test_state)
    
    print("\nResult State:")
    print(state_summary(result_state))
    
    if result_state.get("plan"):
        print("\nPlan:")
        for i, step in enumerate(result_state["plan"], 1):
            print(f"  {i}. {step}")
