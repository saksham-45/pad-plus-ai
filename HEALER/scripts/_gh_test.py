"""Test GitHub connectivity and create repo."""
import json, urllib.request, os, sys

TOKEN = 'github_pat_xxxxxxxxxxxxxxxxxxxx'

def gh_api(method, path, data=None):
    url = f'https://api.github.com{path}'
    req = urllib.request.Request(url, method=method)
    req.add_header('Authorization', f'Bearer {TOKEN}')
    req.add_header('Accept', 'application/vnd.github.v3+json')
    req.add_header('User-Agent', 'HEALER')
    if data:
        req.data = json.dumps(data).encode('utf-8')
        req.add_header('Content-Type', 'application/json')
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        body = json.loads(resp.read()) if resp.status != 204 else {}
        print(f'{method} {path}: {resp.status}')
        return body
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f'{method} {path}: {e.code} {body[:200]}')
        return None
    except Exception as e:
        print(f'{method} {path}: FAIL {e}')
        return None

# Step 1: auth check
print('=== Step 1: Auth check ===')
user = gh_api('GET', '/user')
if user:
    print(f'Authenticated as: {user.get("login")}')

# Step 2: create repo
print('\n=== Step 2: Create repo ===')
repo_data = {
    'name': 'HEALER',
    'description': 'HEALER — self-healing module. Runtime diagnostics, AST patching, meta-learning. Zero external dependencies.',
    'private': False,
    'auto_init': False,
}
result = gh_api('POST', '/user/repos', repo_data)
if result:
    print(f'Repo created: {result.get("clone_url")}')
else:
    # maybe it already exists
    result2 = gh_api('GET', '/repos/ovladimirovich/HEALER')
    if result2:
        print(f'Repo already exists: {result2.get("clone_url")}')
