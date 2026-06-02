import httpx, json
creds = json.load(open("C:/Users/doubl/.config/swecc/bench_credentials.json"))
r = httpx.get(
    "https://api.swecc.org/bench/v1/developer/environments/cf42c6b1-6136-464a-98bf-2d8ebe72ca68",
    headers={"Authorization": f"Bearer {creds['token']}"}
)
print(json.dumps(r.json(), indent=2))
