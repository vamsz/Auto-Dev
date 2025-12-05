"""
Docker Sandbox for the Self-Healing Agent System.

Provides isolated code execution in Docker containers:
- Safe execution of untrusted code
- Persistent container management
- Captures stdout, stderr, and exit codes

This is the critical "Safety Net" that prevents the AI from
accidentally damaging the host system.
"""

import docker
import tempfile
import os
import time
from typing import Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import config


@dataclass
class ExecutionResult:
    """Result of a command execution in the sandbox."""
    stdout: str
    stderr: str
    exit_code: int
    duration_seconds: float
    timed_out: bool = False
    
    @property
    def success(self) -> bool:
        """Check if execution was successful."""
        return self.exit_code == 0 and not self.timed_out
    
    def __str__(self) -> str:
        status = "✓ SUCCESS" if self.success else f"✗ FAILED (exit code: {self.exit_code})"
        output = f"""
{status} - Duration: {self.duration_seconds:.2f}s

=== STDOUT ===
{self.stdout if self.stdout else '(empty)'}

=== STDERR ===
{self.stderr if self.stderr else '(empty)'}
"""
        return output.strip()


class DockerSandbox:
    """
    Docker-based sandbox for safe code execution.
    
    Usage:
        sandbox = DockerSandbox()
        
        # Execute a simple command
        result = sandbox.execute("python --version")
        print(result.stdout)
        
        # Execute with mounted directory
        result = sandbox.execute("pytest", mount_path="./my_project")
        
        # Clean up
        sandbox.cleanup()
    """
    
    def __init__(
        self,
        image: str = None,
        timeout: int = None,
        auto_pull: bool = True
    ):
        """
        Initialize the Docker sandbox.
        
        Args:
            image: Docker image to use (default: from config)
            timeout: Command timeout in seconds (default: from config)
            auto_pull: Automatically pull image if not available
        """
        self.image = image or config.DOCKER_IMAGE
        self.timeout = timeout or config.DOCKER_TIMEOUT
        self.auto_pull = auto_pull
        
        self._client: Optional[docker.DockerClient] = None
        self._container = None
    
    @property
    def client(self) -> docker.DockerClient:
        """Lazy initialization of Docker client."""
        if self._client is None:
            try:
                self._client = docker.from_env()
                # Test connection
                self._client.ping()
            except docker.errors.DockerException as e:
                raise RuntimeError(
                    f"Failed to connect to Docker. Is Docker Desktop running?\n"
                    f"Error: {e}"
                )
        return self._client
    
    def _ensure_image(self):
        """Ensure the Docker image is available."""
        try:
            self.client.images.get(self.image)
        except docker.errors.ImageNotFound:
            if self.auto_pull:
                print(f"Pulling Docker image: {self.image}...")
                self.client.images.pull(self.image)
            else:
                raise RuntimeError(f"Docker image not found: {self.image}")
    
    def execute(
        self,
        command: str,
        mount_path: Optional[str] = None,
        workdir: str = "/workspace",
        env: Optional[dict] = None,
        timeout: Optional[int] = None
    ) -> ExecutionResult:
        """
        Execute a command in an isolated Docker container.
        
        Args:
            command: The command to execute
            mount_path: Optional local path to mount into container
            workdir: Working directory inside container
            env: Optional environment variables
            timeout: Override default timeout
        
        Returns:
            ExecutionResult with stdout, stderr, exit_code
        """
        self._ensure_image()
        
        timeout = timeout or self.timeout
        volumes = {}
        
        # Mount local directory if specified
        if mount_path:
            mount_path = str(Path(mount_path).resolve())
            volumes[mount_path] = {"bind": workdir, "mode": "rw"}
        
        start_time = time.time()
        timed_out = False
        
        try:
            # Run the container
            container = self.client.containers.run(
                self.image,
                command=f"sh -c '{command}'",
                volumes=volumes,
                working_dir=workdir,
                environment=env or {},
                detach=True,
                remove=False,  # We'll remove manually after getting logs
                network_mode="none",  # No network access for security
                mem_limit="512m",  # Limit memory
                cpu_period=100000,
                cpu_quota=50000,  # 50% CPU limit
            )
            
            # Wait for completion with timeout
            try:
                result = container.wait(timeout=timeout)
                exit_code = result.get("StatusCode", -1)
            except Exception:
                # Timeout - kill the container
                timed_out = True
                container.kill()
                exit_code = -1
            
            # Get logs
            stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")
            
            # Clean up container
            container.remove(force=True)
            
        except docker.errors.ContainerError as e:
            stdout = ""
            stderr = str(e)
            exit_code = e.exit_status
            
        except docker.errors.ImageNotFound:
            raise RuntimeError(f"Docker image not found: {self.image}")
            
        except docker.errors.APIError as e:
            raise RuntimeError(f"Docker API error: {e}")
        
        duration = time.time() - start_time
        
        return ExecutionResult(
            stdout=stdout.strip(),
            stderr=stderr.strip(),
            exit_code=exit_code,
            duration_seconds=duration,
            timed_out=timed_out
        )
    
    def execute_python(
        self,
        code: str,
        mount_path: Optional[str] = None
    ) -> ExecutionResult:
        """
        Execute Python code in the sandbox.
        
        Args:
            code: Python code to execute
            mount_path: Optional local path to mount
        
        Returns:
            ExecutionResult
        """
        # Escape single quotes in the code
        escaped_code = code.replace("'", "'\\''")
        command = f"python -c '{escaped_code}'"
        return self.execute(command, mount_path)
    
    def run_pytest(
        self,
        test_path: str = ".",
        mount_path: Optional[str] = None,
        extra_args: str = ""
    ) -> ExecutionResult:
        """
        Run pytest in the sandbox.
        
        Args:
            test_path: Path to tests (relative to mounted workspace)
            mount_path: Local path to mount
            extra_args: Additional pytest arguments
        
        Returns:
            ExecutionResult
        """
        # First install pytest if not in image
        command = f"pip install -q pytest && python -m pytest {test_path} -v {extra_args}"
        return self.execute(command, mount_path)
    
    def run_linter(
        self,
        file_path: str = ".",
        mount_path: Optional[str] = None
    ) -> ExecutionResult:
        """
        Run flake8 linter in the sandbox.
        
        Args:
            file_path: Path to lint (relative to mounted workspace)
            mount_path: Local path to mount
        
        Returns:
            ExecutionResult
        """
        command = f"pip install -q flake8 && python -m flake8 {file_path} --max-line-length=100"
        return self.execute(command, mount_path)
    
    def check_docker_available(self) -> Tuple[bool, str]:
        """
        Check if Docker is available and running.
        
        Returns:
            Tuple of (is_available, message)
        """
        try:
            self.client.ping()
            version = self.client.version()
            return True, f"Docker {version.get('Version', 'unknown')} is running"
        except Exception as e:
            return False, f"Docker is not available: {e}"
    
    def cleanup(self):
        """Clean up Docker client resources."""
        if self._client:
            self._client.close()
            self._client = None


# Convenience function for simple one-off execution
def execute_command(
    command: str,
    mount_path: Optional[str] = None,
    timeout: int = 60
) -> ExecutionResult:
    """
    Execute a command in a Docker sandbox (convenience function).
    
    Args:
        command: Command to execute
        mount_path: Optional path to mount
        timeout: Timeout in seconds
    
    Returns:
        ExecutionResult
    """
    sandbox = DockerSandbox(timeout=timeout)
    try:
        return sandbox.execute(command, mount_path)
    finally:
        sandbox.cleanup()


# Test script
if __name__ == "__main__":
    print("=== Docker Sandbox Test ===\n")
    
    sandbox = DockerSandbox()
    
    # Check Docker availability
    available, message = sandbox.check_docker_available()
    print(f"Docker Status: {message}")
    
    if not available:
        print("\n❌ Docker is not running. Please start Docker Desktop.")
        exit(1)
    
    print("\n--- Test 1: Simple Python execution ---")
    result = sandbox.execute_python("print('Hello from Docker!')")
    print(result)
    
    print("\n--- Test 2: Math calculation ---")
    result = sandbox.execute_python("print(sum(range(100)))")
    print(result)
    
    print("\n--- Test 3: Intentional error ---")
    result = sandbox.execute_python("raise ValueError('This is a test error')")
    print(result)
    
    print("\n--- Test 4: Check Python version ---")
    result = sandbox.execute("python --version")
    print(result)
    
    sandbox.cleanup()
    print("\n✓ All tests completed!")
