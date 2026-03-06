#!/usr/bin/env python3
"""
Railway Deployment Verification Script

Monitors Railway deployments via CLI polling to detect build status,
parse logs for errors, and verify health endpoints.

Usage:
    uv run python scripts/railway_verify.py [--timeout SECONDS] [--verbose]

Exit Codes:
    0 - Deployment verified successfully
    1 - Deployment failed
    2 - Timeout waiting for deployment
    3 - Health check failed
"""

# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "requests>=2.31.0",
# ]
# ///

import argparse
import re
import subprocess
import sys
import time
from typing import Optional

# Default configuration
POLL_INTERVAL = 5  # seconds
MAX_TIMEOUT = 300  # 5 minutes
BUILDING_INDICATORS = ["building", "deploying", "starting", "rebuilding"]
SUCCESS_INDICATORS = ["healthy", "running", "active", "up"]
FAILURE_INDICATORS = ["failed", "crashed", "error", "exited"]

# Error patterns to detect in logs
ERROR_PATTERNS = [
    r"Error:", r"ERROR:", r"error:",
    r"Build failed", r"Failed to build", r"Build error",
    r"No module named", r"Module not found",
    r"SyntaxError", r"IndentationError",
    r"Connection refused", r"timeout",
    r"Traceback", r"Exception",
    r"ImportError", r"DependencyError",
]


class RailwayDeploymentMonitor:
    """Monitors Railway deployment status via CLI polling."""

    def __init__(self, timeout: int = MAX_TIMEOUT, verbose: bool = False):
        self.timeout = timeout
        self.verbose = verbose
        self.start_time = None

    def run_command(self, cmd: list[str]) -> tuple[int, str, str]:
        """Run a command and return exit code, stdout, stderr."""
        if self.verbose:
            print(f"[DEBUG] Running: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if self.verbose and result.stdout:
            print(f"[DEBUG] stdout: {result.stdout[:200]}")
        if self.verbose and result.stderr:
            print(f"[DEBUG] stderr: {result.stderr[:200]}")
        return result.returncode, result.stdout, result.stderr

    def get_deployment_status(self) -> Optional[str]:
        """Get current deployment status from Railway CLI."""
        returncode, stdout, _ = self.run_command(["railway", "status"])

        if returncode != 0:
            if self.verbose:
                print(f"[DEBUG] railway status failed with code {returncode}")
            return None

        # Parse output for status indicators
        output_lower = stdout.lower()

        # Check for failure indicators first
        for indicator in FAILURE_INDICATORS:
            if indicator in output_lower:
                return "failed"

        # Check for building indicators
        for indicator in BUILDING_INDICATORS:
            if indicator in output_lower:
                return "building"

        # Check for success indicators
        for indicator in SUCCESS_INDICATORS:
            if indicator in output_lower:
                return "success"

        # If nothing matched, look at the output more carefully
        if "healthy" in output_lower or "running" in output_lower:
            return "success"

        # Unknown state
        if self.verbose:
            print(f"[DEBUG] Unknown status from: {stdout[:200]}")
        return "unknown"

    def wait_for_completion(self) -> str:
        """Poll deployment status until completion or timeout."""
        self.start_time = time.time()
        last_status = None

        print("Monitoring deployment status...")

        while True:
            elapsed = time.time() - self.start_time

            if elapsed >= self.timeout:
                print(f"Timeout after {elapsed:.0f}s")
                return "timeout"

            status = self.get_deployment_status()

            if status != last_status:
                print(f"  Status: {status} ({elapsed:.0f}s elapsed)")
                last_status = status

            if status == "success":
                print(f"Deployment completed successfully in {elapsed:.0f}s")
                return "success"
            elif status == "failed":
                print(f"Deployment failed after {elapsed:.0f}s")
                return "failed"
            elif status is None:
                print(f"Unable to determine status (Railway CLI error?)")
                return "error"

            # Still building, wait before next poll
            time.sleep(POLL_INTERVAL)


class BuildLogAnalyzer:
    """Analyzes Railway build logs for errors and failure patterns."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        # Compile error patterns for efficiency
        self.compiled_patterns = [re.compile(p, re.IGNORECASE) for p in ERROR_PATTERNS]

    def get_logs(self, tail: int = 100) -> str:
        """Get recent build logs from Railway."""
        result = subprocess.run(
            ["railway", "logs", "--tail", str(tail)],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            if self.verbose:
                print(f"[DEBUG] railway logs failed: {result.stderr}")
            return ""

        return result.stdout

    def analyze_logs(self) -> dict[str, any]:
        """Analyze logs for errors and return summary."""
        logs = self.get_logs()

        errors = []
        for pattern in self.compiled_patterns:
            matches = pattern.finditer(logs)
            for match in matches:
                # Extract the line containing the error
                line_start = logs.rfind('\n', 0, match.start()) + 1
                line_end = logs.find('\n', match.end())
                if line_end == -1:
                    line_end = len(logs)
                error_line = logs[line_start:line_end].strip()
                if error_line and error_line not in errors:
                    errors.append(error_line)

        # Check for success indicators
        success_indicators = [
            "Application startup complete",
            "Uvicorn running on",
            "Application started",
            "startup complete",
        ]
        has_success = any(indicator.lower() in logs.lower() for indicator in success_indicators)

        return {
            "has_errors": len(errors) > 0,
            "error_count": len(errors),
            "errors": errors[:10],  # Limit to first 10 errors
            "has_success": has_success,
            "log_length": len(logs),
        }

    def print_summary(self, analysis: dict[str, any]):
        """Print analysis summary to stdout."""
        if analysis["has_success"]:
            print("✓ Startup detected in logs")

        if analysis["has_errors"]:
            print(f"\n⚠ Found {analysis['error_count']} error(s) in logs:")
            for error in analysis["errors"]:
                print(f"  - {error}")
        else:
            print("✓ No errors detected in logs")


class DeploymentHealthChecker:
    """Verifies health endpoint of deployed service."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def get_domain(self) -> Optional[str]:
        """Get public domain from Railway."""
        result = subprocess.run(
            ["railway", "domain"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            return None

        # Parse domain from output (usually just the URL)
        domain = result.stdout.strip()
        if domain and not domain.startswith("http"):
            domain = f"https://{domain}"

        return domain

    def check_health(self, domain: str) -> bool:
        """Check health endpoint."""
        import requests

        health_url = f"{domain}/health"

        if self.verbose:
            print(f"[DEBUG] Checking health: {health_url}")

        try:
            response = requests.get(health_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                is_healthy = data.get("status") == "healthy"
                if is_healthy:
                    print(f"✓ Health check passed: {health_url}")
                else:
                    print(f"⚠ Health endpoint returned unexpected status: {data}")
                return is_healthy
            else:
                print(f"⚠ Health endpoint returned status {response.status_code}")
                return False
        except requests.exceptions.Timeout:
            print(f"⚠ Health check timed out")
            return False
        except Exception as e:
            print(f"⚠ Health check failed: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Verify Railway deployment status"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=MAX_TIMEOUT,
        help=f"Maximum time to wait for deployment (default: {MAX_TIMEOUT}s)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Railway Deployment Verification")
    print("=" * 60)

    # Step 1: Monitor deployment
    print("\n[1/3] Monitoring deployment status...")
    monitor = RailwayDeploymentMonitor(timeout=args.timeout, verbose=args.verbose)
    status = monitor.wait_for_completion()

    if status == "timeout":
        print("\nDeployment timed out. Check Railway dashboard for status.")
        return 2
    elif status == "failed":
        print("\nDeployment failed. Analyzing logs...")
        analyzer = BuildLogAnalyzer(verbose=args.verbose)
        analysis = analyzer.analyze_logs()
        analyzer.print_summary(analysis)
        return 1
    elif status == "error":
        print("\nUnable to check deployment status. Check Railway CLI and dashboard.")
        return 1

    # Step 2: Analyze logs
    print("\n[2/3] Analyzing build logs...")
    analyzer = BuildLogAnalyzer(verbose=args.verbose)
    analysis = analyzer.analyze_logs()
    analyzer.print_summary(analysis)

    if analysis["has_errors"] and not analysis["has_success"]:
        print("\nDeployment has errors but may still be starting...")
        # Don't fail yet, let health check decide

    # Step 3: Health check
    print("\n[3/3] Verifying health endpoint...")
    checker = DeploymentHealthChecker(verbose=args.verbose)
    domain = checker.get_domain()

    if not domain:
        print("⚠ Could not determine deployment domain")
        return 3

    print(f"Deployment URL: {domain}")

    # Give the service a moment to fully start
    print("Waiting 5 seconds for service to be ready...")
    time.sleep(5)

    health_ok = checker.check_health(domain)

    if not health_ok:
        print("\nHealth check failed. Deployment may not be working correctly.")
        print("Check Railway logs for more details:")
        print("  railway logs --tail 50")
        return 3

    # All checks passed
    print("\n" + "=" * 60)
    print("✓ Deployment verified successfully!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
