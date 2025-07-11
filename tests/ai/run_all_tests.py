#!/usr/bin/env python3
"""
Run all AI system tests with detailed reporting.
"""

import unittest
import sys
import os
import time
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def run_tests():
    """Run all tests and generate report."""
    print("=" * 70)
    print("Monopoly AI System - Test Suite")
    print("=" * 70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test modules
    test_modules = [
        'test_game_event_listener',
        'test_ai_game_manager',
        'test_action_executor',
        'test_integration'
    ]
    
    for module in test_modules:
        try:
            tests = loader.loadTestsFromName(f'tests.ai.{module}')
            suite.addTests(tests)
            print(f"✓ Loaded tests from {module}")
        except Exception as e:
            print(f"✗ Failed to load {module}: {e}")
    
    print()
    print("Running tests...")
    print("-" * 70)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    start_time = time.time()
    result = runner.run(suite)
    end_time = time.time()
    
    # Print summary
    print("-" * 70)
    print("\nTest Summary:")
    print(f"  Total tests run: {result.testsRun}")
    print(f"  Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"  Failures: {len(result.failures)}")
    print(f"  Errors: {len(result.errors)}")
    print(f"  Time taken: {end_time - start_time:.2f} seconds")
    
    # Print failures and errors
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"\n  {test}:")
            print(f"    {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"\n  {test}:")
            print(f"    {traceback}")
    
    # Coverage report (if coverage.py is installed)
    try:
        import coverage
        print("\nGenerating coverage report...")
        cov = coverage.Coverage()
        cov.start()
        
        # Re-run tests with coverage
        runner = unittest.TextTestRunner(verbosity=0)
        runner.run(suite)
        
        cov.stop()
        cov.save()
        
        print("\nCoverage Summary:")
        cov.report(include="src/ai/*")
    except ImportError:
        print("\nNote: Install 'coverage' package for code coverage reports")
    
    print("\n" + "=" * 70)
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Return exit code
    return 0 if result.wasSuccessful() else 1


def run_single_test(test_name: str):
    """Run a single test module."""
    print(f"Running tests from: {test_name}")
    
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName(f'tests.ai.{test_name}')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    if len(sys.argv) > 1:
        # Run specific test module
        exit_code = run_single_test(sys.argv[1])
    else:
        # Run all tests
        exit_code = run_tests()
    
    sys.exit(exit_code)