"""
Node B: The Developer (Coding)

The Developer is responsible for:
1. Reading the content of relevant files
2. Understanding the implementation plan
3. Generating new code based on the plan
4. Writing changes to files
5. Creating test files to verify the work

This is the core coding agent that implements changes.
"""

import json
import re
from pathlib import Path
from typing import List, Dict

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from state.schema import AgentState
from tools.file_tools import read_file, write_file
from config import config


DEVELOPER_SYSTEM_PROMPT = """You are a Senior Python Developer implementing changes to a codebase.

Your responsibilities:
1. Read and understand the existing code
2. Implement the changes according to the plan
3. Follow existing code patterns and style
4. Create or update tests to verify your changes

CRITICAL JSON RULES:
- Output ONLY valid JSON - no markdown, no code blocks, just raw JSON
- Use double quotes for all strings
- Escape newlines in code content as \\n (two characters: backslash and n)
- Escape tabs as \\t
- Escape backslashes as \\\\
- Do NOT include actual line breaks inside string values
- Include the COMPLETE file content in each change

Output this exact JSON structure:
{"changes": [{"action": "modify", "file_path": "path/to/file.py", "content": "full file content with \\n for newlines", "description": "what this change does"}], "test_file": {"file_path": "tests/test_feature.py", "content": "test file content"}, "explanation": "Brief explanation"}

Guidelines:
- Use descriptive variable names
- Add docstrings and comments
- Handle edge cases
- Follow PEP 8 style guidelines
- Make tests specific and meaningful"""


def get_llm():
    """Get configured Groq LLM instance (LLaMA 3)."""
    return ChatGroq(
        model=config.GROQ_MODEL,
        api_key=config.GROQ_API_KEY,
        temperature=0.2  # Slightly higher for creative coding
    )


def developer_node(state: AgentState) -> AgentState:
    """
    The Developer node: Implements code changes based on the plan.
    
    Input state:
        - plan: Implementation steps from Architect
        - relevant_files: Files to work with
        - file_contents: Content of relevant files
        - test_output: Previous test output (if retrying)
        - attempt_count: Current retry attempt
    
    Output state updates:
        - changes_made: List of changes applied
        - file_contents: Updated with new content
        - status: Remains "developing" until done
    """
    print("\n💻 DEVELOPER: Implementing changes...")
    
    state = dict(state)  # Make mutable copy
    attempt = state.get("attempt_count", 0)
    
    print(f"   Attempt: {attempt + 1}/{config.MAX_RETRY_ATTEMPTS}")
    
    # Build context for the LLM
    llm = get_llm()
    
    # Prepare file contents for prompt
    files_context = []
    for file_path, content in state.get("file_contents", {}).items():
        files_context.append(f"### {file_path}\n```python\n{content}\n```")
    
    files_str = "\n\n".join(files_context) if files_context else "No files loaded."
    
    # Prepare plan
    plan_str = "\n".join(f"{i+1}. {step}" for i, step in enumerate(state.get("plan", [])))
    
    # Prepare error context if this is a retry
    error_context = ""
    if attempt > 0 and state.get("test_output"):
        error_context = f"""
## ⚠️ PREVIOUS ATTEMPT FAILED
The previous implementation failed with this error:
```
{state.get("test_output", "Unknown error")}
```

Please fix the issue and try again. Analyze the error carefully and correct the bug.
"""
    
    # Prepare error history for additional context
    error_history = state.get("error_history", [])
    if error_history:
        error_context += f"\n\nError history:\n" + "\n".join(f"- {e}" for e in error_history[-3:])
    
    user_message = f"""
## User Request
{state.get("user_request", "No user request provided")}

## Implementation Plan
{plan_str}

## Current Files
{files_str}

{error_context}

Implement the changes according to the plan. Output valid JSON with 'changes', 'test_file', and 'explanation'.
Make sure to include COMPLETE file contents in your response.
"""

    try:
        print("   Generating code with AI...")
        response = llm.invoke([
            SystemMessage(content=DEVELOPER_SYSTEM_PROMPT),
            HumanMessage(content=user_message)
        ])
        
        response_text = response.content
        
        # Parse JSON from response - robust parsing
        try:
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                json_str = json_match.group()
                
                # Step 1: Remove markdown code blocks if present
                json_str = re.sub(r'^```json\s*', '', json_str)
                json_str = re.sub(r'^```\s*', '', json_str)
                json_str = re.sub(r'\s*```$', '', json_str)
                
                # Step 2: Replace all actual newlines/tabs with escaped versions
                # But preserve the JSON structure
                lines = json_str.split('\n')
                cleaned_lines = []
                in_string = False
                for line in lines:
                    cleaned_lines.append(line)
                json_str = '\n'.join(cleaned_lines)
                
                # Step 3: Remove control characters (except newline, tab for now)
                json_str = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', json_str)
                
                # Step 4: Try to parse
                try:
                    result = json.loads(json_str)
                except json.JSONDecodeError:
                    # Try a more aggressive cleanup
                    # Replace literal newlines in string values with \n
                    # This is a simplified approach
                    json_str = json_str.replace('\r\n', '\\n').replace('\r', '\\n')
                    
                    # Try again
                    try:
                        result = json.loads(json_str)
                    except json.JSONDecodeError:
                        # Last resort: extract just the essential parts manually
                        print("   Attempting manual extraction...")
                        changes = []
                        
                        # Look for file paths and content patterns
                        path_matches = re.findall(r'"file_path"\s*:\s*"([^"]+)"', json_str)
                        content_matches = re.findall(r'"content"\s*:\s*"((?:[^"\\]|\\.)*)"', json_str, re.DOTALL)
                        
                        for i, path in enumerate(path_matches):
                            if i < len(content_matches):
                                content = content_matches[i].replace('\\n', '\n').replace('\\t', '\t')
                                changes.append({
                                    "action": "modify",
                                    "file_path": path,
                                    "content": content,
                                    "description": "Auto-extracted change"
                                })
                        
                        if changes:
                            result = {"changes": changes, "explanation": "Extracted from malformed JSON"}
                        else:
                            raise ValueError("Could not extract any changes from response")
            else:
                raise ValueError("No JSON found in response")
            
            changes = result.get("changes", [])
            test_file = result.get("test_file")
            explanation = result.get("explanation", "")
            
            print(f"   ✓ Generated {len(changes)} file changes")
            if test_file:
                print(f"   ✓ Generated test file: {test_file.get('file_path', 'unknown')}")
            
        except (json.JSONDecodeError, ValueError) as e:
            print(f"   ⚠ JSON parse error: {e}")
            print("   Retrying with simplified request...")
            state["error_history"] = state.get("error_history", []) + [
                f"Developer JSON parse failed: {str(e)}"
            ]
            state["attempt_count"] = attempt + 1
            return state
        
        # Apply changes to files
        changes_made = []
        local_path = Path(state.get("local_path", "."))
        
        for change in changes:
            action = change.get("action", "modify")
            file_path = change.get("file_path", "")
            content = change.get("content", "")
            description = change.get("description", "")
            
            if not file_path or not content:
                continue
            
            full_path = local_path / file_path
            
            try:
                result = write_file(
                    str(full_path),
                    content,
                    create_dirs=True,
                    backup=True
                )
                
                changes_made.append({
                    "file": file_path,
                    "action": action,
                    "description": description,
                    "bytes": result.get("bytes_written", 0)
                })
                
                print(f"   ✓ {action.upper()}: {file_path}")
                
                # Update file_contents cache
                state["file_contents"][file_path] = content
                
            except Exception as e:
                print(f"   ⚠ Failed to write {file_path}: {e}")
                state["error_history"] = state.get("error_history", []) + [
                    f"Write failed for {file_path}: {str(e)}"
                ]
        
        # Write test file
        if test_file and test_file.get("file_path") and test_file.get("content"):
            test_path = local_path / test_file["file_path"]
            try:
                # Make sure tests directory exists
                test_path.parent.mkdir(parents=True, exist_ok=True)
                
                write_file(
                    str(test_path),
                    test_file["content"],
                    create_dirs=True
                )
                
                changes_made.append({
                    "file": test_file["file_path"],
                    "action": "create",
                    "description": "Test file for verification"
                })
                
                print(f"   ✓ CREATE: {test_file['file_path']}")
                
            except Exception as e:
                print(f"   ⚠ Failed to write test file: {e}")
        
        state["changes_made"] = state.get("changes_made", []) + changes_made
        state["status"] = "testing"
        
        if explanation:
            print(f"   Summary: {explanation[:100]}...")
        
        print("   ✓ Development phase complete!")
        
    except Exception as e:
        print(f"   ✗ LLM error: {e}")
        state["error_history"] = state.get("error_history", []) + [
            f"Developer LLM failed: {str(e)}"
        ]
        state["attempt_count"] = attempt + 1
    
    return state


def apply_code_fix(state: AgentState, specific_fix: str) -> AgentState:
    """
    Apply a specific fix without full regeneration.
    Useful for small corrections based on test feedback.
    
    Args:
        state: Current agent state
        specific_fix: Description of the specific fix needed
    
    Returns:
        Updated state
    """
    print(f"\n🔧 DEVELOPER: Applying quick fix...")
    print(f"   Fix: {specific_fix[:80]}...")
    
    llm = get_llm()
    
    # Get the last error and relevant code
    last_error = state.get("test_output", "")
    
    fix_prompt = f"""
A test failed with this error:
```
{last_error}
```

The fix needed is: {specific_fix}

Provide ONLY the corrected code as JSON with the file changes.
Output format:
{{
    "changes": [
        {{
            "file_path": "path/to/file.py",
            "content": "complete corrected content"
        }}
    ]
}}
"""
    
    try:
        response = llm.invoke([
            SystemMessage(content="You are a Python developer fixing a bug. Output only JSON."),
            HumanMessage(content=fix_prompt)
        ])
        
        json_match = re.search(r'\{[\s\S]*\}', response.content)
        if json_match:
            result = json.loads(json_match.group())
            
            local_path = Path(state.get("local_path", "."))
            for change in result.get("changes", []):
                file_path = change.get("file_path")
                content = change.get("content")
                if file_path and content:
                    write_file(str(local_path / file_path), content)
                    print(f"   ✓ Fixed: {file_path}")
                    
    except Exception as e:
        print(f"   ⚠ Quick fix failed: {e}")
    
    return state


# For testing the node directly
if __name__ == "__main__":
    from state.schema import create_initial_state, state_summary
    
    print("=== Developer Node Test ===\n")
    
    # Create test state (simulating post-architect state)
    test_state = create_initial_state(
        repo_url="https://github.com/test/repo",
        user_request="Add a function that calculates fibonacci numbers",
        branch_name="feature/fibonacci"
    )
    
    # Simulate architect output
    test_state["local_path"] = "./test_workspace"
    test_state["relevant_files"] = ["main.py"]
    test_state["file_contents"] = {
        "main.py": "# Main module\n\ndef hello():\n    return 'Hello, World!'"
    }
    test_state["plan"] = [
        "Add fibonacci function to main.py",
        "Create test_fibonacci.py with unit tests"
    ]
    test_state["status"] = "developing"
    
    print("Input State:")
    print(state_summary(test_state))
    
    # Note: This will fail without valid API key
    # result_state = developer_node(test_state)
    # print("\nResult State:")
    # print(state_summary(result_state))
