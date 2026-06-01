import httpx, json
creds = json.load(open("C:/Users/doubl/.config/swecc/bench_credentials.json"))
r = httpx.get(
    "https://api.swecc.org/bench/v1/developer/environments/83cd64c7-3488-4e4c-abbd-134439f5a22a",
    headers={"Authorization": f"Bearer {creds['token']}"}
)
print(json.dumps(r.json(), indent=2))
