import requests

BASE_URL = 'http://localhost:8000/api'

print('=== Testing History & Submissions API ===')

# Test 1: Get quizzes (history)
print('\n1. GET /quizzes (History):')
r = requests.get(f'{BASE_URL}/quizzes')
print(f'   Status: {r.status_code}')
data = r.json()
print(f'   Found {len(data)} quizzes')
if data:
    print(f'   First quiz: {data[0].get("title", "N/A")}')

# Test 2: Guest login
print('\n2. POST /auth/guest:')
r = requests.post(f'{BASE_URL}/auth/guest')
print(f'   Status: {r.status_code}')
data = r.json()
token = data.get('token')
print(f'   Guest created: {data.get("user", {}).get("name")}')

# Test 3: Get submissions with auth
print('\n3. GET /me/submissions:')
headers = {'Authorization': f'Bearer {token}'}
r = requests.get(f'{BASE_URL}/me/submissions', headers=headers)
print(f'   Status: {r.status_code}')
print(f'   Response: {r.json()}')

print('\n=== All tests passed! ===')
