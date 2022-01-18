from urllib import request, parse, error
from collections import OrderedDict
from bs4 import BeautifulSoup, Tag

ANTONLINE_URL = 'https://www.antonline.com/Microsoft/Electronics/Gaming_Devices/Gaming_Consoles/1438909'
ANTONLINE_URL ='https://www.antonline.com/Microsoft/Electronics/Gaming_Devices/Gaming_Consoles/1440078'


headers = OrderedDict({
    'accept': '*/*',
    'accept-language': 'en-US,en;q=0.9',
    'Host': "www.antonline.com",
    'authority': 'www.antonline.com',
    'origin': 'https://www.antonline.com',
    'referer': 'https://www.antonline.com/Microsoft/Electronics/Gaming_Devices/Gaming_Consoles/1438909',
    'pragma': 'no-cache',
    'cache-control': 'no-cache',
    'accounttype': 'Real',
    'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="96", "Google Chrome";v="96"',
    'sec-ch-us-mobile': '?0',
    'sec-ch-ua-platform': 'macOS',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'none',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'x-requested-with': 'XMLHttpRequest',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36 OPR/80.0.4170.63'
})
try:
    req = request.Request(url=ANTONLINE_URL, headers=headers)
    response = request.urlopen(req)
    results = response.read()
    html_results = results.decode('utf-8')
    soup = BeautifulSoup(html_results, "html.parser")
    add_to_cart_buttons = soup.find_all(class_='uk-button uk-disabled')
    text = add_to_cart_buttons[0].text
except error.HTTPError as e:
    results = response.read()
    html_results = results.decode('utf-8')
    print("Error %s retrieving %s" % (e.code, ANTONLINE_URL) )
