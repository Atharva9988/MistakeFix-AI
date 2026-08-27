import json
import urllib.request
import urllib.error

with open("test_examples.json") as f:
    examples = json.load(f)

url = "http://localhost:3000/api/diagnose"
results = []

for ex in examples:
    payload = json.dumps({
        "questionId": ex["id"],
        "question": ex["question"],
        "correctSteps": ex["correctSteps"],
        "studentSteps": ex["studentSteps"]
    }).encode()

    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        response = urllib.request.urlopen(req)
        body = json.loads(response.read())
        got = body.get("mistakeType", "ERROR")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        got = f"REQUEST_FAILED: {error_body}"
    except Exception as e:
        got = f"REQUEST_FAILED: {e}"

    passed = got == ex["category"]
    results.append((ex["id"], ex["category"], got, passed))
    print(f"{ex['id']}: expected={ex['category']} got={got} {'PASS' if passed else 'FAIL'}")

total = len(results)
passed_count = sum(1 for r in results if r[3])
print(f"\n{passed_count}/{total} passed")