import json
from backend.main import get_subjects

result = get_subjects()
print("Python JSON Output:")
print(json.dumps(result, indent=2))
