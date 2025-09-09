import requests
import json

# Test batch upload
url = "http://localhost:8000/file_handler/batch/upload/"

# CHANGE THESE TO YOUR ACTUAL FILES IN SUPABASE
payload = {
    "files": [
        {"path": "test.pdf", "bucket": "linkledger"},
        {"path": "test_document.pdf", "bucket": "linkledger"},
        {"path": "amazon.de.castisebi.pdf", "bucket": "linkledger"},
    ],
    "priority": "normal",
    "batch_name": "Test Batch"
}

response = requests.post(url, json=payload)
print(f"Status: {response.status_code}")
print(json.dumps(response.json(), indent=2))