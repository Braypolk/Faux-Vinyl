import os
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

request = Request('http://127.0.0.1:8787/healthz', headers={'Host': urlsplit(os.environ['PUBLIC_URL']).netloc})
with urlopen(request, timeout=3) as response:
    assert response.status == 200
