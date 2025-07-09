#!/usr/bin/env python3
"""
Download age_modifier model specifically.
"""

import sys
import os

def download_age_modifier_model():
    """Download the age_modifier model."""
    try:
        sys.path.insert(0, '.')
        
        # Import required modules
        from facefusion.processors.modules import age_modifier
        from facefusion.download import conditional_download_hashes, conditional_download_sources
        
        print("Downloading age_modifier model...")
        
        # Get model options
        model_options = age_modifier.get_model_options()
        
        if model_options:
            print("Model options found:")
            print(f"  Hashes: {model_options.get('hashes', {}).keys()}")
            print(f"  Sources: {model_options.get('sources', {}).keys()}")
            
            # Download hashes
            model_hash_set = model_options.get('hashes')
            if model_hash_set:
                print("\nDownloading model hashes...")
                hash_result = conditional_download_hashes(model_hash_set)
                print(f"Hash download result: {hash_result}")
            
            # Download sources
            model_source_set = model_options.get('sources')
            if model_source_set:
                print("\nDownloading model sources...")
                source_result = conditional_download_sources(model_source_set)
                print(f"Source download result: {source_result}")
                
                if hash_result and source_result:
                    print("✅ Age modifier model downloaded successfully!")
                    return True
                else:
                    print("❌ Failed to download age modifier model")
                    return False
            else:
                print("❌ No model sources found")
                return False
        else:
            print("❌ No model options found")
            return False
            
    except Exception as e:
        print(f"❌ Error downloading age_modifier model: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_model_files():
    """Check if model files exist."""
    try:
        print("\nChecking model files...")
        
        model_paths = [
            ".assets/models/styleganex_age.onnx",
            ".assets/models/styleganex_age.hash"
        ]
        
        all_exist = True
        for path in model_paths:
            if os.path.exists(path):
                size = os.path.getsize(path)
                print(f"✅ {path} ({size:,} bytes)")
            else:
                print(f"❌ {path} (not found)")
                all_exist = False
        
        return all_exist
        
    except Exception as e:
        print(f"❌ Error checking model files: {e}")
        return False

def test_age_modifier_after_download():
    """Test age_modifier after downloading the model."""
    try:
        print("\nTesting age_modifier after download...")
        
        sys.path.insert(0, '.')
        from facefusion.processors.modules import age_modifier
        
        # Test pre_check
        pre_check_result = age_modifier.pre_check()
        print(f"Pre-check result: {pre_check_result}")
        
        if pre_check_result:
            print("✅ Age modifier is ready to use!")
            return True
        else:
            print("❌ Age modifier pre-check still fails")
            return False
            
    except Exception as e:
        print(f"❌ Error testing age_modifier: {e}")
        return False

def main():
    print("Age Modifier Model Downloader")
    print("=" * 50)
    
    # Check if models already exist
    if check_model_files():
        print("✅ Age modifier models already exist!")
    else:
        print("⬇️  Downloading age modifier models...")
        download_age_modifier_model()
        
        # Check again after download
        check_model_files()
    
    # Test the module
    test_age_modifier_after_download()
    
    print("\n" + "=" * 50)
    print("NEXT STEPS:")
    print("1. If download was successful, retry your API call")
    print("2. The age_modifier should now work properly")
    print("3. Try with extreme values like -100 or 100 for more visible effects")

if __name__ == "__main__":
    main()
