#!/usr/bin/env python3
"""
Main test runner for FaceFusion API tests.
This script provides an interactive menu to run different test scenarios.
"""

import sys
import os
from test_config import get_test_config
from test_many_faces_api import FaceFusionAPITester
from quick_api_test import test_api_connection, demo_analyze_endpoint, demo_basic_headless_run, demo_many_faces_workflow


def print_banner():
    """Print the test runner banner."""
    print("🎭 FaceFusion API Test Runner")
    print("=" * 60)
    print("Comprehensive testing suite for FaceFusion API endpoints")
    print("Tests include: health check, analyze, headless-run, and --many parameter")
    print("=" * 60)


def print_menu():
    """Print the interactive menu."""
    print("\n📋 Available Test Options:")
    print("1. 🏥 Quick Health Check")
    print("2. 🔍 Test Analyze Endpoint")
    print("3. 🔄 Test Basic Face Swap")
    print("4. 🎭 Test Many Faces Workflow")
    print("5. 🧪 Run Full Test Suite")
    print("6. ⚙️  Show Configuration")
    print("7. 📁 Show File Structure Guide")
    print("8. 🚪 Exit")
    print()


def run_health_check():
    """Run a quick health check."""
    print("\n🏥 Running Health Check...")
    print("-" * 30)
    config = get_test_config()
    success = test_api_connection(config.base_url)
    
    if success:
        print("✅ API server is healthy and ready for testing!")
    else:
        print("❌ API server is not responding. Please check:")
        print("  1. Is the server running? (python start_server.py)")
        print("  2. Is it accessible at the configured URL?")
        print(f"  3. Current URL: {config.base_url}")
    
    return success


def run_analyze_test():
    """Run analyze endpoint test."""
    print("\n🔍 Testing Analyze Endpoint...")
    print("-" * 30)
    config = get_test_config()
    
    # Test with image
    if config.test_files["target_image"] and os.path.exists(config.test_files["target_image"]):
        print("Testing with image...")
        demo_analyze_endpoint(config.test_files["target_image"], config.base_url)
    else:
        print("❌ Target image not found. Please update test_config.py")
        return False
    
    return True


def run_basic_face_swap_test():
    """Run basic face swap test."""
    print("\n🔄 Testing Basic Face Swap...")
    print("-" * 30)
    config = get_test_config()
    
    source = config.test_files["source_image"]
    target = config.test_files["target_image"]
    output = os.path.join(config.test_files["output_dir"], "basic_swap_result.jpg")
    
    if not os.path.exists(source):
        print(f"❌ Source image not found: {source}")
        return False
    
    if not os.path.exists(target):
        print(f"❌ Target image not found: {target}")
        return False
    
    return demo_basic_headless_run(source, target, output, config.base_url)


def run_many_faces_test():
    """Run many faces workflow test."""
    print("\n🎭 Testing Many Faces Workflow...")
    print("-" * 30)
    config = get_test_config()
    
    sources = config.test_files["source_images"]
    target = config.test_files["target_image"]
    output = os.path.join(config.test_files["output_dir"], "many_faces_result.jpg")
    
    # Check if source files exist
    missing_sources = [s for s in sources if not os.path.exists(s)]
    if missing_sources:
        print("❌ Missing source images:")
        for source in missing_sources:
            print(f"  - {source}")
        return False
    
    if not os.path.exists(target):
        print(f"❌ Target image not found: {target}")
        return False
    
    return demo_many_faces_workflow(sources, target, output, config.base_url)


def run_full_test_suite():
    """Run the complete test suite."""
    print("\n🧪 Running Full Test Suite...")
    print("-" * 30)
    config = get_test_config()
    
    # Check configuration first
    missing_files = config.get_missing_files()
    if missing_files:
        print("⚠️  Some test files are missing:")
        for file_path in missing_files:
            print(f"  - {file_path}")
        print()
        response = input("Continue with available tests? (y/N): ").strip().lower()
        if response != 'y':
            return False
    
    # Create test configuration for the full suite
    test_config = {
        "source_image": config.test_files["source_image"],
        "source_images": config.test_files["source_images"],
        "target_image": config.test_files["target_image"],
        "target_video": config.test_files["target_video"]
    }
    
    # Initialize and run the full test suite
    tester = FaceFusionAPITester(config.base_url)
    tester.run_all_tests(test_config)
    
    return True


def show_configuration():
    """Show current test configuration."""
    print("\n⚙️  Current Test Configuration")
    print("-" * 30)
    config = get_test_config()
    config.print_config_summary()


def show_file_structure_guide():
    """Show file structure guide."""
    print("\n📁 Test Files Structure Guide")
    print("-" * 30)
    config = get_test_config()
    config.create_sample_files_structure()


def main():
    """Main interactive menu."""
    print_banner()
    
    # Initial health check
    if not run_health_check():
        print("\n⚠️  API server is not responding. Some tests may fail.")
        response = input("Continue anyway? (y/N): ").strip().lower()
        if response != 'y':
            print("Exiting. Please start the API server and try again.")
            sys.exit(1)
    
    while True:
        print_menu()
        
        try:
            choice = input("Select an option (1-8): ").strip()
            
            if choice == "1":
                run_health_check()
            
            elif choice == "2":
                run_analyze_test()
            
            elif choice == "3":
                run_basic_face_swap_test()
            
            elif choice == "4":
                run_many_faces_test()
            
            elif choice == "5":
                run_full_test_suite()
            
            elif choice == "6":
                show_configuration()
            
            elif choice == "7":
                show_file_structure_guide()
            
            elif choice == "8":
                print("\n👋 Goodbye!")
                break
            
            else:
                print("❌ Invalid option. Please select 1-8.")
            
            # Pause before showing menu again
            if choice in ["1", "2", "3", "4", "5"]:
                input("\nPress Enter to continue...")
        
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            input("Press Enter to continue...")


if __name__ == "__main__":
    main()
