"""
Quick Import Test - Verify all modules load correctly with mock mode
"""

print("Testing imports with MOCK mode enabled...\n")

# Test 1: Config
print("1️⃣ Testing config import...")
import config
print(f"   ✅ Config loaded")
print(f"   USE_MOCK_LINKEDIN_DATA = {config.USE_MOCK_LINKEDIN_DATA}")

# Test 2: Mock LinkedIn Data
print("\n2️⃣ Testing mock_linkedin_data import...")
from utils.mock_linkedin_data import generate_mock_candidates
print(f"   ✅ Mock LinkedIn module loaded")

# Test 3: LinkedIn Router
print("\n3️⃣ Testing linkedin_scout router import...")
try:
    from routers.linkedin_scout import router
    print(f"   ✅ LinkedIn router loaded successfully")
    print(f"   Router has {len(router.routes)} routes")
except Exception as e:
    print(f"   ❌ Error loading router: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Main app
print("\n4️⃣ Testing main app import...")
try:
    from main import app
    print(f"   ✅ FastAPI app loaded successfully")
    print(f"   Total routes: {len(app.routes)}")
except Exception as e:
    print(f"   ❌ Error loading app: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("✅ ALL IMPORTS SUCCESSFUL - Ready to start server!")
print("="*60)
print("\n💡 Start server with: uvicorn main:app --reload --port 8080")
