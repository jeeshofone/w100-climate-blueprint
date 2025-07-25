#!/usr/bin/env python3
"""Setup development environment to match GitHub Actions exactly."""

import sys
import os
import subprocess
import platform
from pathlib import Path


def run_command(cmd, description=""):
    """Run a command and return success status."""
    if description:
        print(f"📦 {description}")
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    
    success = result.returncode == 0
    if success:
        print("✅ Success")
    else:
        print("❌ Failed")
    
    print("-" * 50)
    return success


def check_python_version():
    """Check Python version matches GitHub Actions."""
    version = sys.version_info
    print(f"🐍 Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major != 3 or version.minor < 11:
        print("⚠️  Warning: GitHub Actions uses Python 3.11+")
        print("   Consider using Python 3.11 or 3.12 for consistency")
    else:
        print("✅ Python version is compatible with GitHub Actions")
    
    print("-" * 50)


def setup_environment():
    """Set up development environment to match GitHub Actions."""
    print("🚀 Setting up W100 Smart Control development environment")
    print("   This will match exactly what GitHub Actions does")
    print("=" * 60)
    
    # Check Python version
    check_python_version()
    
    # Change to project root
    project_root = Path(__file__).parent
    os.chdir(project_root)
    print(f"📁 Working directory: {project_root}")
    print("-" * 50)
    
    # Step 1: Upgrade pip (same as GitHub Actions)
    if not run_command(
        [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
        "Upgrading pip (GitHub Actions Step 1)"
    ):
        return False
    
    # Step 2: Install test dependencies (same as GitHub Actions)
    if not run_command(
        [sys.executable, "-m", "pip", "install", "-r", "requirements_test.txt"],
        "Installing test dependencies (GitHub Actions Step 2)"
    ):
        return False
    
    # Verify installation
    print("🔍 Verifying installation...")
    
    # Check pytest
    if not run_command([sys.executable, "-m", "pytest", "--version"], "Checking pytest"):
        return False
    
    # Check black
    if not run_command([sys.executable, "-m", "black", "--version"], "Checking black"):
        return False
    
    # Check coverage
    if not run_command([sys.executable, "-c", "import coverage; print(f'coverage {coverage.__version__}')"], "Checking coverage"):
        return False
    
    print("🎉 Development environment setup complete!")
    print("")
    print("📋 Available commands (same as GitHub Actions):")
    print("   make test          # Run tests with coverage")
    print("   make lint          # Run linting checks")
    print("   make type-check    # Run type checking")
    print("   make github-all    # Simulate complete GitHub Actions")
    print("")
    print("   python run_tests.py --all  # Alternative test runner")
    print("")
    print("🔗 Your local environment now matches GitHub Actions exactly!")
    
    return True


def main():
    """Main setup function."""
    try:
        success = setup_environment()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n⚠️  Setup interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())