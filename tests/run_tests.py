#!/usr/bin/env python3
"""
Test runner for elasticsearch_lib tests.

This script runs all tests and generates a coverage report.
"""

import sys
import os
import subprocess
from pathlib import Path

# Add the parent directory to the Python path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))


def run_tests():
    """Run all tests with coverage reporting."""
    print("=" * 60)
    print("Running elasticsearch_lib Test Suite")
    print("=" * 60)
    
    # Change to the project root directory
    os.chdir(parent_dir)
    
    # Run pytest with coverage
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",
        "--tb=short",
        "--cov=elasticsearch_lib",
        "--cov=user_search_handler",
        "--cov=search_users_tool",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "--cov-fail-under=80"
    ]
    
    try:
        result = subprocess.run(cmd, check=False)
        
        print("\n" + "=" * 60)
        if result.returncode == 0:
            print("✅ All tests passed!")
            print("📊 Coverage report generated in htmlcov/index.html")
        else:
            print("❌ Some tests failed or coverage is below threshold")
            print("📊 Coverage report generated in htmlcov/index.html")
        print("=" * 60)
        
        return result.returncode
        
    except FileNotFoundError:
        print("❌ Error: pytest not found. Please install pytest and pytest-cov:")
        print("   pip install pytest pytest-cov")
        return 1
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1


def run_specific_test(test_file):
    """Run a specific test file."""
    print(f"Running tests from {test_file}")
    
    # Change to the project root directory
    os.chdir(parent_dir)
    
    cmd = [
        sys.executable, "-m", "pytest",
        f"tests/{test_file}",
        "-v",
        "--tb=short"
    ]
    
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except Exception as e:
        print(f"❌ Error running test: {e}")
        return 1


def check_dependencies():
    """Check if required test dependencies are installed."""
    required_packages = ["pytest", "pytest-cov"]
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\nInstall them with:")
        print(f"   pip install {' '.join(missing_packages)}")
        return False
    
    return True


def main():
    """Main test runner function."""
    if len(sys.argv) > 1:
        # Run specific test file
        test_file = sys.argv[1]
        if not test_file.startswith("test_"):
            test_file = f"test_{test_file}"
        if not test_file.endswith(".py"):
            test_file = f"{test_file}.py"
        
        return run_specific_test(test_file)
    else:
        # Check dependencies first
        if not check_dependencies():
            return 1
        
        # Run all tests
        return run_tests()


if __name__ == "__main__":
    sys.exit(main())
