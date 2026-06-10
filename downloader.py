import requests

url = "https://api.cijene.dev/v0/archive/2026-06-09.zip"

response = requests.get(url)

with open("archive.zip", "wb") as file:
    file.write(response.content)

print("ZIP preuzet!")