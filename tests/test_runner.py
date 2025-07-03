#!/usr/bin/env python3
"""Simple test runner script for the MCP server."""

import subprocess
import sys


def run_tests():
    """Run all tests with coverage reporting."""
    print("Running MCP Server Tests...")
    print("=" * 50)
    
    try:
        # Run pytest with coverage
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "-v", 
            "--cov=zbx_mcp_server",
            "--cov-report=term-missing",
            "--cov-report=html"
        ], check=True)
        
        print("\n" + "=" * 50)
        print("✅ All tests passed!")
        print("📊 Coverage report generated in htmlcov/")
        return 0
        
    except subprocess.CalledProcessError as e:
        print("\n" + "=" * 50)
        print("❌ Tests failed!")
        return e.returncode
    except FileNotFoundError:
        print("❌ pytest not found. Please install test dependencies:")
        print("   pip install -e .[test]")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())