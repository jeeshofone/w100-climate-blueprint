#!/usr/bin/env python3
"""Test runner for W100 Smart Control integration."""

import sys
import os
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, cwd=None):
    """Run a command and return the result."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    
    return result.returncode == 0


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description="Run W100 Smart Control tests")
    parser.add_argument("--coverage", action="store_true", help="Run with coverage")
    parser.add_argument("--lint", action="store_true", help="Run linting")
    parser.add_argument("--type-check", action="store_true", help="Run type checking")
    parser.add_argument("--all", action="store_true", help="Run all checks")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if args.all:
        args.coverage = True
        args.lint = True
        args.type_check = True
    
    # Change to project root
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    success = True
    
    # Install test dependencies (same as GitHub Actions)
    print("Installing test dependencies...")
    print("Running: python -m pip install --upgrade pip")
    if not run_command([sys.executable, "-m", "pip", "install", "--upgrade", "pip"]):
        print("Failed to upgrade pip")
        return 1
    
    if not run_command([sys.executable, "-m", "pip", "install", "-r", "requirements_test.txt"]):
        print("Failed to install test dependencies")
        return 1
    
    # Run tests (same as GitHub Actions)
    print("\n" + "="*50)
    print("Running tests...")
    print("="*50)
    
    test_cmd = [sys.executable, "-m", "pytest", "tests/"]
    
    if args.verbose:
        test_cmd.append("-v")
    else:
        test_cmd.append("-v")  # Always verbose like GitHub Actions
    
    if args.coverage:
        test_cmd.extend([
            "--cov=custom_components/w100_smart_control",
            "--cov-report=term-missing",
            "--cov-report=xml"
        ])
    
    if not run_command(test_cmd):
        print("Tests failed!")
        success = False
    
    # Run linting
    if args.lint:
        print("\n" + "="*50)
        print("Running linting...")
        print("="*50)
        
        # Black
        print("Running black...")
        if not run_command([sys.executable, "-m", "black", "--check", "--diff", "custom_components/"]):
            print("Black formatting check failed!")
            success = False
        
        # isort
        print("Running isort...")
        if not run_command([sys.executable, "-m", "isort", "--check-only", "--diff", "custom_components/"]):
            print("isort import sorting check failed!")
            success = False
        
        # flake8
        print("Running flake8...")
        if not run_command([sys.executable, "-m", "flake8", "custom_components/"]):
            print("flake8 linting failed!")
            success = False
    
    # Run type checking
    if args.type_check:
        print("\n" + "="*50)
        print("Running type checking...")
        print("="*50)
        
        if not run_command([sys.executable, "-m", "mypy", "custom_components/", "--ignore-missing-imports"]):
            print("Type checking failed!")
            success = False
    
    # Summary
    print("\n" + "="*50)
    if success:
        print("✅ All checks passed!")
        return 0
    else:
        print("❌ Some checks failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())