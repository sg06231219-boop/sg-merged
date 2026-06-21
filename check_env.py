import os, requests, subprocess, sys

HF_TOKEN = os.environ.get('HF_TOKEN', '')
if not HF_TOKEN:
    print('ERROR: HF_TOKEN not set')
    sys.exit(1)

# Check git
result = subprocess.run(['git', '--version'], capture_output=True, text=True)
print(f'Git: {result.stdout.strip()}')

# Check HF CLI
try:
    result = subprocess.run(['huggingface-cli', '--version'], capture_output=True, text=True)
    print(f'HF CLI: {result.stdout.strip()}')
except:
    print('HF CLI: NOT FOUND, will use direct upload')

# Check space
space_repo = 'LZ-SG/SG-Site-Builder'
headers = {'Authorization': f'Bearer {HF_TOKEN}'}
r = requests.get(f'https://huggingface.co/api/spaces/{space_repo}', headers=headers)
print(f'Space: {r.status_code}')
if r.ok:
    info = r.json()
    print(f"  SDK: {info.get('sdk')} {info.get('sdk_version')}")
