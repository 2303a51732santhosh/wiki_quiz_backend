import requests

# Test API endpoints
BASE_URL = "http://localhost:8000/api"

print("=" * 50)
print("Testing WikiQuiz AI API")
print("=" * 50)

# Test 1: Get quizzes (no auth)
print("\n1. Testing GET /api/quizzes (no auth)...")
try:
    response = requests.get(f"{BASE_URL}/quizzes")
    print(f"   Status: {response.status_code}")
    data = response.json()
    print(f"   Found {len(data)} quizzes")
    if data:
        print(f"   First quiz: {data[0]['title'][:50]}...")
except Exception as e:
    print(f"   ERROR: {e}")

# Test 2: Guest login
print("\n2. Testing POST /api/auth/guest...")
try:
    response = requests.post(f"{BASE_URL}/auth/guest")
    print(f"   Status: {response.status_code}")
    data = response.json()
    token = data.get('token')
    user = data.get('user', {})
    print(f"   User: {user.get('name')} (Guest: {user.get('is_guest')})")
    print(f"   Token: {token[:20]}...")
except Exception as e:
    print(f"   ERROR: {e}")

# Test 3: Get quizzes with auth
print("\n3. Testing GET /api/quizzes (with guest auth)...")
try:
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/quizzes", headers=headers)
    print(f"   Status: {response.status_code}")
    data = response.json()
    print(f"   Found {len(data)} quizzes for guest user")
except Exception as e:
    print(f"   ERROR: {e}")

# Test 4: User signup
print("\n4. Testing POST /api/auth/signup...")
import random
email = f"test{random.randint(1000,9999)}@example.com"
try:
    response = requests.post(f"{BASE_URL}/auth/signup", json={
        "email": email,
        "password": "test123",
        "name": "Test User"
    })
    print(f"   Status: {response.status_code}")
    data = response.json()
    if response.status_code == 200:
        print(f"   Created user: {data.get('user', {}).get('email')}")
        user_token = data.get('token')
    else:
        print(f"   Response: {data}")
except Exception as e:
    print(f"   ERROR: {e}")

print("\n" + "=" * 50)
print("All tests completed!")
print("=" * 50)
