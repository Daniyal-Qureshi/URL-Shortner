import requests



def get_ip_info(ip_address):
    url = f"https://ipinfo.io/{ip_address}/json"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return {
            "ip": data.get("ip"),
            "city": data.get("city"),
            "region": data.get("region"),
            "country": data.get("country"),
            "loc": data.get("loc"),
            "org": data.get("org"),
            "postal": data.get("postal"),
            "timezone": data.get("timezone"),
            "readme": data.get("readme")
        }
    else:
        return {"error": "Unable to retrieve data"}