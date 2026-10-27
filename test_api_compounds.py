import urllib.request, json, time
time.sleep(1)

# Health check
req = urllib.request.Request('http://localhost:8000/api/health')
with urllib.request.urlopen(req, timeout=5) as r:
    print('Health:', r.read().decode())

# Test compounds endpoint
payload = json.dumps({
    'disease': 'type 2 diabetes',
    'targets': [{'symbol': 'PPARG', 'name': 'PPAR gamma'}],
    'synonyms': ['T2DM']
}).encode()

req2 = urllib.request.Request(
    'http://localhost:8000/api/compounds',
    data=payload,
    headers={'Content-Type': 'application/json'},
    method='POST'
)

with urllib.request.urlopen(req2, timeout=120) as r:
    data = json.loads(r.read().decode())

print('Status:', data['status'])
print('Total compounds:', data['total_compounds'])
print('Route A:', data['route_a_count'], '| Route B:', data['route_b_count'], '| Dual:', data['dual_route_count'])
for c in data['compounds'][:6]:
    print(f"  - {c['name'][:30]:30s}  dual={c['is_dual_route']}  routes={c['retrieval_routes']}")
