"""
Comprehensive test runner for Headquarters Finder application.

This script runs all tests including unit tests, integration tests,
edge case tests, and golden path tests with coverage reporting.
"""

import pytest
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_all_tests():
    """Run all tests with coverage reporting."""
    print("🚀 RUNNING COMPREHENSIVE TEST SUITE")
    print("=" * 60)
    
    # Test directories
    test_dirs = [
        "tests/unit",
        "tests/integration", 
        "tests/edge_cases",
        "tests/golden_path"
    ]
    
    # Run tests with coverage
    pytest_args = [
        "-v",  # Verbose output
        "--tb=short",  # Short traceback format
        "--cov=headquarters_finder",  # Coverage for main package
        "--cov-report=html",  # HTML coverage report
        "--cov-report=term-missing",  # Terminal coverage report
        "--cov-report=xml",  # XML coverage report
        "--cov-fail-under=80",  # Fail if coverage below 80%
        "--junitxml=test-results.xml",  # JUnit XML report
        "--html=test-report.html",  # HTML test report
        "--self-contained-html",  # Self-contained HTML
        "--maxfail=10",  # Stop after 10 failures
        "--durations=10",  # Show 10 slowest tests
        "--strict-markers",  # Strict marker checking
        "--strict-config",  # Strict config checking
        "--disable-warnings",  # Disable warnings
        "--color=yes",  # Colored output
        "--tb=line",  # Line traceback format
        "--capture=no",  # Don't capture output
        "--log-cli-level=INFO",  # Log level
        "--log-cli-format=%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
        "--log-cli-date-format=%Y-%m-%d %H:%M:%S",
        "--log-file=test.log",  # Log file
        "--log-file-level=DEBUG",  # Log file level
        "--log-file-format=%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
        "--log-file-date-format=%Y-%m-%d %H:%M:%S",
        "--log-auto-indent=true",  # Auto indent logs
        "--log-disable=[]",  # Don't disable any loggers
        "--log-enable=[]",  # Enable all loggers
        "--log-level=INFO",  # Log level
        "--log-format=%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
        "--log-date-format=%Y-%m-%d %H:%M:%S",
        "--log-cli-level=INFO",
        "--log-cli-format=%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
        "--log-cli-date-format=%Y-%m-%d %H:%M:%S",
        "--log-file=test.log",
        "--log-file-level=DEBUG",
        "--log-file-format=%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
        "--log-file-date-format=%Y-%m-%d %H:%M:%S",
        "--log-auto-indent=true",
        "--log-disable=[]",
        "--log-enable=[]",
        "--log-level=INFO",
        "--log-format=%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
        "--log-date-format=%Y-%m-%d %H:%M:%S"
    ]
    
    # Add test directories
    pytest_args.extend(test_dirs)
    
    # Run tests
    exit_code = pytest.main(pytest_args)
    
    if exit_code == 0:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Unit tests: PASSED")
        print("✅ Integration tests: PASSED")
        print("✅ Edge case tests: PASSED")
        print("✅ Golden path tests: PASSED")
        print("✅ Coverage: 80%+")
        print("\n📊 Reports generated:")
        print("  - HTML Coverage Report: htmlcov/index.html")
        print("  - HTML Test Report: test-report.html")
        print("  - XML Coverage Report: coverage.xml")
        print("  - JUnit XML Report: test-results.xml")
        print("  - Test Log: test.log")
    else:
        print(f"\n❌ TESTS FAILED (Exit code: {exit_code})")
        print("Please check the test output above for details.")
    
    return exit_code


def run_unit_tests():
    """Run only unit tests."""
    print("🧪 RUNNING UNIT TESTS")
    print("=" * 40)
    
    pytest_args = [
        "-v",
        "--tb=short",
        "--cov=headquarters_finder",
        "--cov-report=term-missing",
        "tests/unit"
    ]
    
    exit_code = pytest.main(pytest_args)
    
    if exit_code == 0:
        print("\n✅ UNIT TESTS PASSED!")
    else:
        print(f"\n❌ UNIT TESTS FAILED (Exit code: {exit_code})")
    
    return exit_code


def run_integration_tests():
    """Run only integration tests."""
    print("🔗 RUNNING INTEGRATION TESTS")
    print("=" * 40)
    
    pytest_args = [
        "-v",
        "--tb=short",
        "--cov=headquarters_finder",
        "--cov-report=term-missing",
        "tests/integration"
    ]
    
    exit_code = pytest.main(pytest_args)
    
    if exit_code == 0:
        print("\n✅ INTEGRATION TESTS PASSED!")
    else:
        print(f"\n❌ INTEGRATION TESTS FAILED (Exit code: {exit_code})")
    
    return exit_code


def run_edge_case_tests():
    """Run only edge case tests."""
    print("⚠️ RUNNING EDGE CASE TESTS")
    print("=" * 40)
    
    pytest_args = [
        "-v",
        "--tb=short",
        "--cov=headquarters_finder",
        "--cov-report=term-missing",
        "tests/edge_cases"
    ]
    
    exit_code = pytest.main(pytest_args)
    
    if exit_code == 0:
        print("\n✅ EDGE CASE TESTS PASSED!")
    else:
        print(f"\n❌ EDGE CASE TESTS FAILED (Exit code: {exit_code})")
    
    return exit_code


def run_golden_path_tests():
    """Run only golden path tests."""
    print("🌟 RUNNING GOLDEN PATH TESTS")
    print("=" * 40)
    
    pytest_args = [
        "-v",
        "--tb=short",
        "--cov=headquarters_finder",
        "--cov-report=term-missing",
        "tests/golden_path"
    ]
    
    exit_code = pytest.main(pytest_args)
    
    if exit_code == 0:
        print("\n✅ GOLDEN PATH TESTS PASSED!")
    else:
        print(f"\n❌ GOLDEN PATH TESTS FAILED (Exit code: {exit_code})")
    
    return exit_code


def run_coverage_report():
    """Run coverage report only."""
    print("📊 GENERATING COVERAGE REPORT")
    print("=" * 40)
    
    pytest_args = [
        "--cov=headquarters_finder",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--cov-report=xml",
        "--cov-fail-under=80",
        "tests/"
    ]
    
    exit_code = pytest.main(pytest_args)
    
    if exit_code == 0:
        print("\n✅ COVERAGE REPORT GENERATED!")
        print("📊 HTML Coverage Report: htmlcov/index.html")
        print("📊 XML Coverage Report: coverage.xml")
    else:
        print(f"\n❌ COVERAGE REPORT FAILED (Exit code: {exit_code})")
    
    return exit_code


def main():
    """Main test runner function."""
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
        
        if test_type == "unit":
            return run_unit_tests()
        elif test_type == "integration":
            return run_integration_tests()
        elif test_type == "edge":
            return run_edge_case_tests()
        elif test_type == "golden":
            return run_golden_path_tests()
        elif test_type == "coverage":
            return run_coverage_report()
        else:
            print(f"Unknown test type: {test_type}")
            print("Available types: unit, integration, edge, golden, coverage, all")
            return 1
    else:
        return run_all_tests()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
