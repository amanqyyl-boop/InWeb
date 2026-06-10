import urllib.request, json

API = 'http://127.0.0.1:5000/api'

def api(path, method='GET', data=None):
    url = API + path
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers={'Content-Type':'application/json'}, method=method)
    try: return json.loads(urllib.request.urlopen(req).read())
    except urllib.error.HTTPError as e: return json.loads(e.read())

# 测试1: 科幻偏好+浏览科幻
u1 = api('/register', 'POST', {'username':'p_sc2','password':'123','preferences':['科幻']})
if 'error' in u1:
    u1 = api('/login', 'POST', {'username':'p_sc2','password':'123'})
uid1 = u1['id']
print('用户1 ID:', uid1, '偏好:', u1.get('preferences',[]))

for b in ['f028','n12','f027']:
    api('/browse', 'POST', {'user_id':uid1, 'novel_id':b})
    n = api('/novels/'+b)
    print('  浏览:', n['title'], n['category'])

r1 = api('/recommend/'+str(uid1))
print('\n=== 用户1 CNN (科幻偏好+浏览科幻) ===')
for x in r1[:8]:
    print(' ', x['title'], '('+x['category']+')', x['rating'])

# 测试2: 仅偏好无浏览
u2 = api('/register', 'POST', {'username':'p_hist2','password':'123','preferences':['历史','军事']})
if 'error' in u2:
    u2 = api('/login', 'POST', {'username':'p_hist2','password':'123'})
uid2 = u2['id']
print('\n用户2 ID:', uid2, '偏好:', u2.get('preferences',[]), '(无浏览)')

r2 = api('/recommend/'+str(uid2))
print('=== 用户2 CNN (仅历史+军事偏好) ===')
for x in r2[:8]:
    print(' ', x['title'], '('+x['category']+')', x['rating'])
