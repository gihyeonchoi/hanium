import whois

url = "https://m.bunjang.co.kr"
ip = "3.171.185.43"

print(whois.whois(url))


import geoip2.database

country_reader = geoip2.database.Reader("GeoLite2-Country.mmdb")
# 테스트용 IP
response = country_reader.country(ip)
print("국가명:", response)