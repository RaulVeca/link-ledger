#!/usr/bin/env python
"""
Simple test to verify temporalio is installed and working correctly
"""

print("Testing Temporal installation...")

# Test 1: Import temporalio
try:
    import temporalio
    print(f"✓ temporalio imported successfully")
    if hasattr(temporalio, '__version__'):
        print(f"  Version: {temporalio.__version__}")
except ImportError as e:
    print(f"✗ Failed to import temporalio: {e}")
    print("\nPlease install temporalio:")
    print("  pip install temporalio")
    exit(1)

# Test 2: Import activity module
try:
    from temporalio import activity
    print(f"✓ temporalio.activity imported successfully")
except ImportError as e:
    print(f"✗ Failed to import activity: {e}")
    exit(1)

# Test 3: Check if defn decorator exists
if hasattr(activity, 'defn'):
    print(f"✓ activity.defn decorator found")
else:
    print(f"✗ activity.defn decorator not found")
    print(f"  Available attributes: {dir(activity)}")
    exit(1)

# Test 4: Try to decorate a simple function
@activity.defn(name="test_activity")
async def test_activity(name: str) -> str:
    return f"Hello, {name}!"

if hasattr(test_activity, '_defn'):
    print(f"✓ Test activity decorated successfully")
    print(f"  Activity name: {test_activity._defn.name}")
else:
    print(f"✗ Test activity decoration failed")
    print(f"  Type: {type(test_activity)}")
    print(f"  Attributes: {dir(test_activity)}")
    exit(1)

# Test 5: Import workflow module
try:
    from temporalio import workflow
    print(f"✓ temporalio.workflow imported successfully")
except ImportError as e:
    print(f"✗ Failed to import workflow: {e}")

print("\n✅ All tests passed! Temporalio is installed correctly.")
print("\nNow testing your actual activity...")

# Test 6: Try to import your activity
try:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from temporal_app.activities import process_file_activity
    print(f"✓ Your process_file_activity imported")
    
    if hasattr(process_file_activity, '_defn'):
        print(f"✓ Your activity is properly decorated")
        print(f"  Activity name: {process_file_activity._defn.name}")
    else:
        print(f"✗ Your activity is NOT decorated")
        print(f"  Function name: {process_file_activity.__name__}")
        
        # Try manual decoration
        print("\nAttempting manual decoration...")
        decorated = activity.defn(name="process_file_activity")(process_file_activity)
        if hasattr(decorated, '_defn'):
            print(f"✓ Manual decoration successful")
            print(f"  You need to update your activities.py file")
        else:
            print(f"✗ Manual decoration failed - there may be an issue with the function signature")
            
except ImportError as e:
    print(f"✗ Failed to import your activity: {e}")
except Exception as e:
    print(f"✗ Error testing your activity: {e}")

print("\n" + "="*60)
print("RECOMMENDATIONS:")
print("="*60)
print("""
If your activity is not being decorated:

1. Make sure you're using the exact decorator syntax:
   @activity.defn(name="process_file_activity")
   async def process_file_activity(args: dict) -> str:

2. Ensure the function is async and has type hints

3. Try reinstalling temporalio:
   pip uninstall temporalio
   pip install temporalio

4. Check Python version (should be 3.8+):
   python --version
""")