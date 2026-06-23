import requests
token = "8044801915:AAEG-EbSh-1f1m5fFwq4xxX_lZSbUjGhsmQ"
url = f'https://api.telegram.org/bot{token}/getUpdates'
requests.post(url).json()
print(requests.post(url).json())