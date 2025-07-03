#!/usr/bin/env python3
"""
Clean test runner for FaceFusion API service tests.
This script ensures a clean Python environment to avoid module conflicts.
"""

import sys
import os
import subprocess
from pathlib import Path


def main():
    """Run tests with a clean Python environment."""
    print("🧪 FaceFusion API Service Tests (Clean Environment)")
    print("=" * 50)
    
    # Get current project directory
    project_root = Path(__file__).parent.absolute()
    
    # Create clean environment variables
    env = os.environ.copy()
    
    # Set clean PYTHONPATH - only include current project and essential system paths
    clean_python_paths = [
        str(project_root),  # Current project first
    ]
    
    # Add essential system paths (but exclude conflicting ones)
    for path in sys.path:
        if path and not any(conflict in path for conflict in [
            '/home/ubuntu/tts/GPT-SoVITS',
            'GPT-SoVITS'
        ]):
            if path not in clean_python_paths:
                clean_python_paths.append(path)
    
    env['PYTHONPATH'] = os.pathsep.join(clean_python_paths)
    
    print("🔧 Environment setup:")
    print(f"   Project root: {project_root}")
    print(f"   Clean PYTHONPATH: {len(clean_python_paths)} paths")
    print("=" * 50)
    
    # Run tests using subprocess with clean environment
    test_command = [
        sys.executable, '-m', 'unittest', 
        'tests.test_api_services', '-v'
    ]
    
    try:
        print("🚀 Running tests...")
        result = subprocess.run(
            test_command, 
            cwd=str(project_root),
            env=env,
            capture_output=False  # Show output in real-time
        )
        
        print("\n" + "=" * 50)
        if result.returncode == 0:
            print("✅ All tests passed!")
        else:
            print(f"❌ Tests failed with return code: {result.returncode}")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
