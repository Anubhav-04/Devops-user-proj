import pytest
import requests
import os
import tempfile
import shutil
import csv
import time
from pathlib import Path

BASE_URL = "http://localhost:3000"

# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------

@pytest.fixture
def temp_image_file():
    """Create a temporary image file (fake) for upload."""
    fd, path = tempfile.mkstemp(suffix='.png')
    with os.fdopen(fd, 'w') as f:
        f.write('fake image content')
    yield path
    if os.path.exists(path):
        os.unlink(path)

@pytest.fixture
def temp_csv_file():
    fd, path = tempfile.mkstemp(suffix='.csv')
    with os.fdopen(fd, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['name', 'email', 'age', 'city'])
        writer.writerow(['Alice', 'alice@example.com', '28', 'New York'])
        writer.writerow(['Bob', 'bob@example.com', '32', 'London'])
    yield path
    if os.path.exists(path):
        os.unlink(path)

@pytest.fixture
def temp_malicious_csv_file():
    """CSV with formula injection payload."""
    fd, path = tempfile.mkstemp(suffix='.csv')
    with os.fdopen(fd, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['name', 'email', 'age', 'city'])
        writer.writerow(['=2+5', 'inj@ex.com', '20', 'Danger'])
    yield path
    if os.path.exists(path):
        os.unlink(path)

@pytest.fixture
def created_user():
    """Create a user and return its ID; delete after test."""
    payload = {
        "name": "Temp User",
        "email": "temp@example.com",
        "age": 25,
        "city": "TempCity"
    }
    resp = requests.post(f"{BASE_URL}/api/users", data=payload)
    assert resp.status_code == 200
    user_id = resp.json()["user"]["_id"]
    yield user_id
    # Teardown: delete the user
    requests.delete(f"{BASE_URL}/api/users/{user_id}")

# ----------------------------------------------------------------------
# Unit Tests
# ----------------------------------------------------------------------

class TestCreateUser:
    def test_valid_user_with_image(self, temp_image_file):
        """UT-01: Create user with valid data and image"""
        with open(temp_image_file, 'rb') as img:
            files = {'image': img}
            data = {'name': 'John', 'email': 'john@ex.com', 'age': 25, 'city': 'NYC'}
            resp = requests.post(f"{BASE_URL}/api/users", data=data, files=files)
        assert resp.status_code == 200
        json_data = resp.json()
        assert json_data['message'] == 'User saved'
        assert json_data['user']['name'] == 'John'
        assert json_data['user']['image'] is not None
        # Cleanup
        user_id = json_data['user']['_id']
        requests.delete(f"{BASE_URL}/api/users/{user_id}")

    def test_user_without_image(self):
        """UT-02: Create user without image"""
        data = {'name': 'Jane', 'email': 'jane@ex.com', 'age': 30, 'city': 'LA'}
        resp = requests.post(f"{BASE_URL}/api/users", data=data)
        assert resp.status_code == 200
        json_data = resp.json()
        assert json_data['user']['image'] is None
        # Cleanup
        user_id = json_data['user']['_id']
        requests.delete(f"{BASE_URL}/api/users/{user_id}")

    def test_missing_required_field(self):
        """UT-03: Missing name field (should return error)"""
        data = {'email': 'x@y.com', 'age': 20, 'city': 'Paris'}
        resp = requests.post(f"{BASE_URL}/api/users", data=data)
        # Expect 500 because schema validation missing (Mongoose required fails)
        assert resp.status_code == 500

    def test_non_image_file_upload(self, temp_image_file):
        """UT-04: Upload a text file as image (currently accepted)"""
        # Rename temp file to .txt (still contains fake content)
        txt_path = temp_image_file.replace('.png', '.txt')
        os.rename(temp_image_file, txt_path)
        try:
            with open(txt_path, 'rb') as f:
                files = {'image': f}
                data = {'name': 'Hacker', 'email': 'hack@ex.com', 'age': 22, 'city': 'Any'}
                resp = requests.post(f"{BASE_URL}/api/users", data=data, files=files)
            assert resp.status_code == 200
            user_id = resp.json()['user']['_id']
            # Should have stored the file (security issue)
            assert resp.json()['user']['image'] is not None
            requests.delete(f"{BASE_URL}/api/users/{user_id}")
        finally:
            if os.path.exists(txt_path):
                os.unlink(txt_path)

    def test_duplicate_email(self):
        """UT-05: Try to create two users with same email (if unique index)"""
        data1 = {'name': 'First', 'email': 'dup@ex.com', 'age': 20, 'city': 'A'}
        data2 = {'name': 'Second', 'email': 'dup@ex.com', 'age': 25, 'city': 'B'}
        resp1 = requests.post(f"{BASE_URL}/api/users", data=data1)
        assert resp1.status_code == 200
        user1_id = resp1.json()['user']['_id']
        resp2 = requests.post(f"{BASE_URL}/api/users", data=data2)
        # If unique index exists, should fail (500)
        assert resp2.status_code == 500
        # Cleanup
        requests.delete(f"{BASE_URL}/api/users/{user1_id}")

    def test_invalid_age_type(self):
        """UT-06: Age as non-numeric string"""
        data = {'name': 'Invalid', 'email': 'inv@ex.com', 'age': 'twenty', 'city': 'X'}
        resp = requests.post(f"{BASE_URL}/api/users", data=data)
        assert resp.status_code == 500  # CastError

class TestGetUsers:
    def test_get_users_empty(self):
        """UT-07: No users in DB"""
        # Assuming DB is empty or we delete all after test? Better to isolate.
        # For reliability, we can create a temp user and delete it, but test emptiness.
        # Alternatively, we can check that response is a list.
        resp = requests.get(f"{BASE_URL}/api/users")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_users_multiple(self, created_user):
        """UT-08: Multiple users present"""
        # created_user fixture creates one user; add another manually
        data = {'name': 'Second', 'email': 'second@ex.com', 'age': 40, 'city': 'Paris'}
        resp = requests.post(f"{BASE_URL}/api/users", data=data)
        assert resp.status_code == 200
        second_id = resp.json()['user']['_id']

        resp_get = requests.get(f"{BASE_URL}/api/users")
        users = resp_get.json()
        assert len(users) >= 2
        # Cleanup second user
        requests.delete(f"{BASE_URL}/api/users/{second_id}")

    def test_image_url_format(self, created_user):
        """UT-09: Verify image URL is correct"""
        # created_user has no image; create a user with image
        with tempfile.NamedTemporaryFile(suffix='.jpg', mode='w+b') as f:
            f.write(b'fake')
            f.seek(0)
            files = {'image': f}
            data = {'name': 'WithImg', 'email': 'img@ex.com', 'age': 30, 'city': 'ImgCity'}
            resp = requests.post(f"{BASE_URL}/api/users", data=data, files=files)
        assert resp.status_code == 200
        user = resp.json()['user']
        assert user['image'].startswith('/uploads/')
        # Cleanup
        requests.delete(f"{BASE_URL}/api/users/{user['_id']}")

class TestSearch:
    @pytest.mark.parametrize("query,expected_name", [
        ("?name=ali", "Alice"),
        ("?name=ALICE", "Alice"),   # case insensitive
        ("?email=bob@example.com", "Bob"),
        ("?name=xxx", None),
    ])
    def test_search(self, query, expected_name):
        # Setup: create Alice and Bob
        users = [
            {'name': 'Alice', 'email': 'alice@example.com', 'age': 28, 'city': 'NYC'},
            {'name': 'Bob', 'email': 'bob@example.com', 'age': 32, 'city': 'London'}
        ]
        ids = []
        for u in users:
            resp = requests.post(f"{BASE_URL}/api/users", data=u)
            assert resp.status_code == 200
            ids.append(resp.json()['user']['_id'])

        resp_search = requests.get(f"{BASE_URL}/api/users/search{query}")
        assert resp_search.status_code == 200
        results = resp_search.json()
        if expected_name:
            assert len(results) >= 1
            assert any(r['name'] == expected_name for r in results)
        else:
            assert len(results) == 0

        # Cleanup
        for uid in ids:
            requests.delete(f"{BASE_URL}/api/users/{uid}")

    def test_search_empty_query(self):
        """UT-14: Empty query returns all users"""
        # Create a user
        data = {'name': 'Temp', 'email': 't@t.com', 'age': 1, 'city': 'T'}
        resp = requests.post(f"{BASE_URL}/api/users", data=data)
        uid = resp.json()['user']['_id']
        resp_search = requests.get(f"{BASE_URL}/api/users/search")
        assert resp_search.status_code == 200
        all_users = resp_search.json()
        assert len(all_users) >= 1
        requests.delete(f"{BASE_URL}/api/users/{uid}")

class TestCSVUpload:
    def test_valid_csv_upload(self, temp_csv_file):
        """UT-15: Valid CSV import"""
        with open(temp_csv_file, 'rb') as f:
            files = {'file': f}
            resp = requests.post(f"{BASE_URL}/api/users/upload-csv", files=files, timeout=5)
        assert resp.status_code == 200
        data = resp.json()
        assert data['message'] == 'CSV users imported'
        assert data['count'] == 2
        # Verify users exist
        resp_get = requests.get(f"{BASE_URL}/api/users")
        users = resp_get.json()
        emails = [u['email'] for u in users]
        assert 'alice@example.com' in emails
        assert 'bob@example.com' in emails
        # Cleanup (delete them)
        for email in ['alice@example.com', 'bob@example.com']:
            # find id and delete
            for u in users:
                if u['email'] == email:
                    requests.delete(f"{BASE_URL}/api/users/{u['_id']}")
                    break

    def test_csv_missing_columns(self):
        """UT-16: CSV missing required column (email)"""
        fd, path = tempfile.mkstemp(suffix='.csv')
        with os.fdopen(fd, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['name', 'age', 'city'])  # no email
            writer.writerow(['NoEmail', '25', 'X'])
        try:
            with open(path, 'rb') as f:
                files = {'file': f}
                resp = requests.post(f"{BASE_URL}/api/users/upload-csv", files=files)
            # Expect failure (500) because email required in schema? Possibly.
            assert resp.status_code == 500
        finally:
            os.unlink(path)

    def test_empty_csv(self):
        """UT-17: Empty CSV (only headers)"""
        fd, path = tempfile.mkstemp(suffix='.csv')
        with os.fdopen(fd, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['name', 'email', 'age', 'city'])
        try:
            with open(path, 'rb') as f:
                files = {'file': f}
                resp = requests.post(f"{BASE_URL}/api/users/upload-csv", files=files)
            assert resp.status_code == 200
            assert resp.json()['count'] == 0
        finally:
            os.unlink(path)

    def test_malformed_csv(self):
        """UT-19: Malformed CSV (random text)"""
        fd, path = tempfile.mkstemp(suffix='.csv')
        with os.fdopen(fd, 'w') as f:
            f.write("This is not a CSV, just some text")
        try:
            with open(path, 'rb') as f:
                files = {'file': f}
                resp = requests.post(f"{BASE_URL}/api/users/upload-csv", files=files)
            # csv-parser will emit no data, so count 0 and success
            assert resp.status_code == 200
            assert resp.json()['count'] == 0
        finally:
            os.unlink(path)

class TestDelete:
    def test_delete_single_user(self, created_user):
        """UT-20: Delete existing user"""
        user_id = created_user
        resp = requests.delete(f"{BASE_URL}/api/users/{user_id}")
        assert resp.status_code == 200
        assert resp.json()['message'] == 'User deleted'
        # Verify deletion
        get_resp = requests.get(f"{BASE_URL}/api/users")
        assert not any(u['_id'] == user_id for u in get_resp.json())

    def test_delete_nonexistent_user(self):
        """UT-21: Delete non-existent ID (valid format)"""
        fake_id = "607f1f77bcf86cd799439011"  # random valid ObjectId
        resp = requests.delete(f"{BASE_URL}/api/users/{fake_id}")
        assert resp.status_code == 200  # API returns success even if not found

    def test_delete_invalid_id_format(self):
        """UT-22: Invalid ID format (not ObjectId)"""
        resp = requests.delete(f"{BASE_URL}/api/users/invalid-id")
        assert resp.status_code == 500  # CastError

class TestBulkDelete:
    def test_bulk_delete_multiple(self):
        """UT-23: Delete multiple existing IDs"""
        # Create two users
        ids = []
        for i in range(2):
            data = {'name': f'Bulk{i}', 'email': f'bulk{i}@ex.com', 'age': 20+i, 'city': 'C'}
            resp = requests.post(f"{BASE_URL}/api/users", data=data)
            ids.append(resp.json()['user']['_id'])

        resp_del = requests.delete(f"{BASE_URL}/api/users", json={'ids': ids})
        assert resp_del.status_code == 200
        assert resp_del.json()['deletedCount'] == 2

    def test_bulk_delete_some_nonexistent(self):
        """UT-24: Some IDs do not exist"""
        ids = ["607f1f77bcf86cd799439011"]  # valid but non-existent
        # plus create one real user
        data = {'name': 'Real', 'email': 'real@ex.com', 'age': 30, 'city': 'R'}
        resp = requests.post(f"{BASE_URL}/api/users", data=data)
        real_id = resp.json()['user']['_id']
        ids.append(real_id)

        resp_del = requests.delete(f"{BASE_URL}/api/users", json={'ids': ids})
        assert resp_del.status_code == 200
        assert resp_del.json()['deletedCount'] == 1

    def test_bulk_delete_empty_ids(self):
        """UT-25: Empty IDs array"""
        resp = requests.delete(f"{BASE_URL}/api/users", json={'ids': []})
        assert resp.status_code == 400
        assert 'No user IDs provided' in resp.json()['message']

    def test_bulk_delete_invalid_id_in_array(self):
        """UT-26: Array contains invalid ObjectId"""
        resp = requests.delete(f"{BASE_URL}/api/users", json={'ids': ['badid']})
        assert resp.status_code == 500  # CastError

class TestUpdate:
    def test_update_all_fields_without_image(self, created_user):
        """UT-27: Update all fields, no new image"""
        user_id = created_user
        update_data = {
            'name': 'UpdatedName',
            'email': 'updated@ex.com',
            'age': 99,
            'city': 'NewCity'
        }
        resp = requests.put(f"{BASE_URL}/api/users/{user_id}", data=update_data)
        assert resp.status_code == 200
        updated = resp.json()['user']
        assert updated['name'] == 'UpdatedName'
        assert updated['email'] == 'updated@ex.com'
        assert updated['age'] == 99
        assert updated['city'] == 'NewCity'

    def test_update_partial_fields(self, created_user):
        """UT-28: Update only name"""
        user_id = created_user
        update_data = {'name': 'OnlyNameChanged'}
        resp = requests.put(f"{BASE_URL}/api/users/{user_id}", data=update_data)
        assert resp.status_code == 200
        updated = resp.json()['user']
        assert updated['name'] == 'OnlyNameChanged'
        # Other fields unchanged? Need to fetch original from fixture? 
        # Since we don't have original, we can check that they exist.
        assert updated['email'] is not None

    def test_update_with_new_image(self, created_user, temp_image_file):
        """UT-29: Update with new image"""
        user_id = created_user
        with open(temp_image_file, 'rb') as img:
            files = {'image': img}
            data = {'name': 'ImageUpdated'}
            resp = requests.put(f"{BASE_URL}/api/users/{user_id}", data=data, files=files)
        assert resp.status_code == 200
        updated = resp.json()['user']
        assert updated['name'] == 'ImageUpdated'
        assert updated['image'] is not None
        assert updated['image'].startswith('/uploads/')

    def test_update_nonexistent_user(self):
        """UT-30: Update non-existent user (valid ID)"""
        fake_id = "607f1f77bcf86cd799439011"
        resp = requests.put(f"{BASE_URL}/api/users/{fake_id}", data={'name': 'Any'})
        assert resp.status_code == 200  # API returns 200 with user: null
        assert resp.json()['user'] is None

    def test_update_invalid_id_format(self):
        """UT-31: Invalid ID format"""
        resp = requests.put(f"{BASE_URL}/api/users/badid", data={'name': 'x'})
        assert resp.status_code == 500

# ----------------------------------------------------------------------
# Load / Performance Tests (simple examples)
# ----------------------------------------------------------------------
@pytest.mark.load
def test_sustained_get_users():
    """LT-01: Simple load test - 100 requests to GET /api/users"""
    times = []
    for _ in range(100):
        start = time.time()
        resp = requests.get(f"{BASE_URL}/api/users")
        end = time.time()
        assert resp.status_code == 200
        times.append(end - start)
    p95 = sorted(times)[int(0.95 * len(times))]
    print(f"p95 response time: {p95:.3f}s")
    assert p95 < 0.5  # 500ms threshold

@pytest.mark.load
def test_burst_create_users():
    """LT-02: Create 10 users concurrently (simulate with loop)"""
    import threading
    def create_user(i):
        data = {'name': f'Load{i}', 'email': f'load{i}@test.com', 'age': i, 'city': 'Load'}
        resp = requests.post(f"{BASE_URL}/api/users", data=data)
        assert resp.status_code == 200
        return resp.json()['user']['_id']

    threads = []
    ids = []
    def target(i):
        uid = create_user(i)
        ids.append(uid)

    for i in range(10):
        t = threading.Thread(target=target, args=(i,))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    # Cleanup
    for uid in ids:
        requests.delete(f"{BASE_URL}/api/users/{uid}")

# ----------------------------------------------------------------------
# Penetration / Security Tests
# ----------------------------------------------------------------------

class TestSecurity:
    def test_malicious_file_upload(self):
        """PT-01: Upload PHP file disguised as image"""
        fd, path = tempfile.mkstemp(suffix='.php')
        with os.fdopen(fd, 'w') as f:
            f.write("<?php system($_GET['cmd']); ?>")
        try:
            with open(path, 'rb') as f:
                files = {'image': f}
                data = {'name': 'Attacker', 'email': 'att@ex.com', 'age': 20, 'city': 'Hack'}
                resp = requests.post(f"{BASE_URL}/api/users", data=data, files=files)
            # Currently multer stores any file; we assert it still succeeds (security issue)
            assert resp.status_code == 200
            user_id = resp.json()['user']['_id']
            # Check that file is stored with .php extension (dangerous)
            image_path = resp.json()['user']['image']
            assert image_path.endswith('.php')  # should be blocked in secure app
            # Cleanup
            requests.delete(f"{BASE_URL}/api/users/{user_id}")
        finally:
            os.unlink(path)

    def test_path_traversal_filename(self):
        """PT-02: Filename containing ../ to escape uploads directory"""
        # Create a file with malicious name
        fd, path = tempfile.mkstemp()  # actual temp file
        malicious_name = "../../../etc/passwd"
        # We'll need to send a file with that name; multer uses originalname from request.
        # We can craft a multipart/form-data with custom filename.
        import requests
        files = {
            'image': (malicious_name, open(path, 'rb'), 'image/png')
        }
        data = {'name': 'Traversal', 'email': 'traverse@ex.com', 'age': 20, 'city': 'Hack'}
        resp = requests.post(f"{BASE_URL}/api/users", data=data, files=files)
        os.unlink(path)
        # Check if file was stored with original name (multer prepends timestamp, but includes original)
        assert resp.status_code == 200
        user = resp.json()['user']
        stored_path = user['image']
        # stored_path like /uploads/1234567890-../../../etc/passwd
        # This could be a path traversal if the web server serves uploads
        assert "passwd" in stored_path
        # Cleanup (also check if file actually written outside uploads? Hard to test automatically)
        requests.delete(f"{BASE_URL}/api/users/{user['_id']}")

    def test_csv_formula_injection(self, temp_malicious_csv_file):
        """PT-03: CSV with formula injection"""
        with open(temp_malicious_csv_file, 'rb') as f:
            files = {'file': f}
            resp = requests.post(f"{BASE_URL}/api/users/upload-csv", files=files)
        assert resp.status_code == 200
        # Verify the =2+5 was stored as is (unsafe)
        # Find the user with email inj@ex.com
        resp_get = requests.get(f"{BASE_URL}/api/users")
        users = resp_get.json()
        inj_user = next(u for u in users if u['email'] == 'inj@ex.com')
        assert inj_user['name'] == '=2+5'  # Stored raw
        # Cleanup
        requests.delete(f"{BASE_URL}/api/users/{inj_user['_id']}")

    def test_large_file_upload_dos(self):
        """PT-04: Upload very large file to cause DoS"""
        # Create a 100MB dummy file
        large_file = tempfile.NamedTemporaryFile(suffix='.bin', delete=False)
        large_file.write(b'0' * 100 * 1024 * 1024)
        large_file.close()
        try:
            with open(large_file.name, 'rb') as f:
                files = {'image': f}
                data = {'name': 'Large', 'email': 'large@ex.com', 'age': 20, 'city': 'Big'}
                resp = requests.post(f"{BASE_URL}/api/users", data=data, files=files, timeout=10)
            # Should either reject or handle; currently may crash server or timeout
            # We expect either 413 (payload too large) or 500, but not 200.
            assert resp.status_code != 200
        except requests.exceptions.Timeout:
            # Timeout is also a failure mode (DoS)
            pytest.fail("Request timed out - possible DoS")
        finally:
            os.unlink(large_file.name)

    def test_nosql_injection_search(self):
        """PT-05: NoSQL injection attempt in search"""
        # Try to pass operator in query
        resp = requests.get(f"{BASE_URL}/api/users/search?name[$ne]=null")
        # The code uses RegExp, so it will treat the whole string as pattern, not operator.
        # Should return 200 (safe) and likely no results because name contains '$ne' literally.
        assert resp.status_code == 200
        # If injection were successful, it would return all users. Let's ensure it doesn't.
        # We can create a user and see if it's returned.
        data = {'name': 'Safe', 'email': 'safe@ex.com', 'age': 1, 'city': 'S'}
        resp_post = requests.post(f"{BASE_URL}/api/users", data=data)
        uid = resp_post.json()['user']['_id']
        resp_search = requests.get(f"{BASE_URL}/api/users/search?name[$ne]=null")
        users = resp_search.json()
        # The user 'Safe' should not be returned because its name is 'Safe', not '$ne'
        assert not any(u['name'] == 'Safe' for u in users)
        requests.delete(f"{BASE_URL}/api/users/{uid}")

    def test_xss_stored(self):
        """PT-07: Store XSS payload in name"""
        xss_payload = "<script>alert(1)</script>"
        data = {'name': xss_payload, 'email': 'xss@ex.com', 'age': 20, 'city': 'XSS'}
        resp = requests.post(f"{BASE_URL}/api/users", data=data)
        assert resp.status_code == 200
        user_id = resp.json()['user']['_id']
        # Retrieve user and check if payload is stored as is
        resp_get = requests.get(f"{BASE_URL}/api/users/{user_id}")
        # Note: there's no GET /api/users/:id endpoint, so use search or all
        resp_all = requests.get(f"{BASE_URL}/api/users")
        users = resp_all.json()
        stored = next(u for u in users if u['_id'] == user_id)
        assert stored['name'] == xss_payload  # Stored unsanitized
        # Cleanup
        requests.delete(f"{BASE_URL}/api/users/{user_id}")

    def test_rate_limiting_abuse(self):
        """PT-11: Simulate brute force creation (if rate limiting absent)"""
        # Send 50 rapid requests
        responses = []
        for i in range(50):
            data = {'name': f'Rate{i}', 'email': f'rate{i}@test.com', 'age': i, 'city': 'R'}
            resp = requests.post(f"{BASE_URL}/api/users", data=data)
            responses.append(resp)
        # All should succeed if no rate limiting
        success_count = sum(1 for r in responses if r.status_code == 200)
        assert success_count > 40  # Most succeed
        # Cleanup created users
        for i in range(50):
            # find by email? Not efficient, but we can use search
            search = requests.get(f"{BASE_URL}/api/users/search?email=rate{i}@test.com")
            users = search.json()
            for u in users:
                requests.delete(f"{BASE_URL}/api/users/{u['_id']}")
