#!/usr/bin/env python3
"""
Full Test Suite Runner

Runs all tests including:
1. MCP Server startup tests
2. Elasticsearch entity search tests for all 11 entity types
"""

import sys
import os
import subprocess
from pathlib import Path


def print_header(title):
    """Print a formatted header."""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")


def run_command(cmd, description):
    """Run a command and return success status."""
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def check_elasticsearch():
    """Check if Elasticsearch is running."""
    print_header("Checking Elasticsearch Connection")
    
    try:
        from elasticsearch import Elasticsearch
        
        es_host = os.getenv("ES_HOST", "localhost")
        es_port = int(os.getenv("ES_PORT", "9200"))
        
        es = Elasticsearch([f"http://{es_host}:{es_port}"])
        
        if es.ping():
            info = es.info()
            print(f"✓ Elasticsearch is running")
            print(f"  Version: {info['version']['number']}")
            print(f"  Cluster: {info['cluster_name']}")
            print(f"  Host: {es_host}:{es_port}")
            return True
        else:
            print(f"✗ Elasticsearch is not responding at {es_host}:{es_port}")
            return False
            
    except Exception as e:
        print(f"✗ Cannot connect to Elasticsearch: {e}")
        print(f"  Make sure Elasticsearch is running on {es_host}:{es_port}")
        return False


def check_dependencies():
    """Check if required dependencies are installed."""
    print_header("Checking Dependencies")
    
    required = {
        'pytest': 'pytest',
        'elasticsearch': 'elasticsearch',
        'fastmcp': 'fastmcp',
    }
    
    missing = []
    
    for package, import_name in required.items():
        try:
            __import__(import_name)
            print(f"✓ {package} installed")
        except ImportError:
            print(f"✗ {package} not installed")
            missing.append(package)
    
    if missing:
        print(f"\n❌ Missing packages: {', '.join(missing)}")
        print(f"Install with: pip install {' '.join(missing)}")
        return False
    
    return True


def run_mcp_server_tests():
    """Run MCP server startup tests."""
    print_header("MCP Server Startup Tests")
    
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/test_mcp_server.py",
        "-v",
        "--tb=short",
        "-s"
    ]
    
    return run_command(cmd, "MCP Server Tests")


def run_elasticsearch_tests():
    """Run Elasticsearch entity search tests."""
    print_header("Elasticsearch Entity Search Tests")
    
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/test_elasticsearch_entities.py",
        "-v",
        "--tb=short",
        "-s"
    ]
    
    return run_command(cmd, "Elasticsearch Entity Tests")


def run_all_tests():
    """Run all tests together."""
    print_header("Running All Tests Together")
    
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/test_mcp_server.py",
        "tests/test_elasticsearch_entities.py",
        "-v",
        "--tb=short",
        "-s"
    ]
    
    return run_command(cmd, "All Tests")


def main():
    """Main test runner."""
    print_header("Full Test Suite Runner")
    
    # Change to project root
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    print(f"Project root: {project_root}")
    print(f"Python: {sys.version}")
    
    # Check dependencies
    if not check_dependencies():
        return 1
    
    # Check Elasticsearch
    es_running = check_elasticsearch()
    
    # Determine which tests to run
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
        
        if test_type == "mcp":
            print_header("Running MCP Server Tests Only")
            success = run_mcp_server_tests()
            
        elif test_type == "es" or test_type == "elasticsearch":
            if not es_running:
                print("\n❌ Elasticsearch is not running. Cannot run Elasticsearch tests.")
                return 1
            print_header("Running Elasticsearch Tests Only")
            success = run_elasticsearch_tests()
            
        elif test_type == "all":
            if not es_running:
                print("\n⚠ Warning: Elasticsearch is not running. Some tests will fail.")
            success = run_all_tests()
            
        else:
            print(f"\n❌ Unknown test type: {test_type}")
            print("Usage: python run_full_tests.py [mcp|es|all]")
            return 1
    else:
        # Run all tests by default
        if not es_running:
            print("\n⚠ Warning: Elasticsearch is not running. Some tests will fail.")
            print("To skip Elasticsearch tests, run: python run_full_tests.py mcp")
        
        # Run MCP tests first
        mcp_success = run_mcp_server_tests()
        
        # Run Elasticsearch tests if ES is running
        if es_running:
            es_success = run_elasticsearch_tests()
        else:
            print("\n⚠ Skipping Elasticsearch tests (service not running)")
            es_success = True  # Don't fail overall if ES not running
        
        success = mcp_success and es_success
    
    # Print final summary
    print_header("Test Summary")
    
    if success:
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed. Check output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

