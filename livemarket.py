import requests
from bs4 import BeautifulSoup
from pprint import pprint

url = "https://www.napanta.com/market-price/karnataka/bangalore/bangalore/15-dec-2025"
response = requests.get(url)
soup = BeautifulSoup(response.content, "html.parser")

# Find the table with class "table table-bordered table-striped"
table = soup.find("table")
if table:
    result = [['Commodity', 'City', 'Variety', 'Maximum Price',	'Average Price', 'Minimum Price', 'Last Updated On']]
    rows = table.find_all("tr")
    for row in rows:
        cells = row.find_all("td")
        if cells:
            d = [cell.get_text(strip=True) for cell in cells]
            result.append(d[:-1])
pprint(result)