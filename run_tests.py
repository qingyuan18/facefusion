#!/usr/bin/env python3
"""
Simple test runner for FaceFusion API service tests.
"""

import sys
import unittest
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def main():
    """Run the API service tests."""
    print("🧪 FaceFusion API Service Tests")
    print("=" * 40)
    print("Testing:")
    print("1. Analyze endpoint (original video analysis)")
    print("2. Headless-run endpoint (single face swap)")
    print("3. Many faces functionality (multi-face mapping)")
    print("4. S3 workflow (specific test case)")
    print("=" * 40)
    
    # Discover and run tests
    loader = unittest.TestLoader()
    suite = loader.discover('tests', pattern='test_api_*.py')
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 40)
    if result.wasSuccessful():
        print("✅ All tests passed!")
    else:
        print(f"❌ {len(result.failures)} test(s) failed")
        print(f"❌ {len(result.errors)} test(s) had errors")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
