from requests import get
from time import sleep
import json

civicjson_urls = ["https://raw.githubusercontent.com/rasmi/my-neighborhood/master/civic.json",
"https://raw.githubusercontent.com/BetaNYC/civic.json/master/civic.json",
"https://raw.githubusercontent.com/ameensol/dataExplorer/master/civic.json",
"https://raw.githubusercontent.com/ameensol/dataExplorerAPI/master/civic.json",
"https://raw.githubusercontent.com/BetaNYC/betanyc-support-ribbon-css/master/civic.json",
"https://raw.githubusercontent.com/BetaNYC/NY-Waterways-GTFS-data/master/civic.json",
"https://raw.githubusercontent.com/rasmi/homeless-nyc/master/civic.json",
"https://raw.githubusercontent.com/MTA-Service-Alerts-beta-nyc/service-alerts/master/civic.json",
"https://raw.githubusercontent.com/seanluciotolentino/dangerous-intersections/master/civic.json",
"https://raw.githubusercontent.com/clhenrick/am-i-rent-stabilized/master/civic.json",
"https://raw.githubusercontent.com/josselinphilippe/bagitnyc/master/civic.json",
"https://raw.githubusercontent.com/hondacivicapps/hondacivicapps.github.io/master/civic.json",
"https://raw.githubusercontent.com/codefordc/guides/master/civic.json",
"https://raw.githubusercontent.com/DangerousRDNYC/DangerousRDNYC/master/civic.json",
"https://raw.githubusercontent.com/Emrals/Emrals-Android/master/civic.json",
"https://raw.githubusercontent.com/codefordc/dc-campaign-finance-watch/master/civic.json",
"https://raw.githubusercontent.com/rasmi/crime-nyc/master/civic.json",
"https://raw.githubusercontent.com/codefordc/open211/master/civic.json",
"https://raw.githubusercontent.com/codefordc/ancfinder/master/civic.json",
"https://raw.githubusercontent.com/codefordc/codefordc-2.0/master/civic.json",
"https://raw.githubusercontent.com/codefordc/districthousing/master/civic.json",
"https://raw.githubusercontent.com/childcaremap/NYCdaycare/master/civic.json",
"https://raw.githubusercontent.com/NYPDVisionZeroAccountability/compstat-vs-moving-violation-enforcement/master/civic.json",
"https://raw.githubusercontent.com/BetaNYC/Bike-Share-Data-Best-Practices/master/civic.json",
"https://raw.githubusercontent.com/BetaNYC/budgetBuddy/master/civic.json",
"https://raw.githubusercontent.com/talos/acris-bigquery/master/civic.json",
"https://raw.githubusercontent.com/camsys/onebusaway-nyc-atstop/master/civic.json"]

key_counts = {
    # key : count
}
key_values = {
    # key : [values]
}

for url in civicjson_urls:
    got = get(url)
    try:
        civicjson = got.json()
    except ValueError:
        pass

    if civicjson:
        for key, value in civicjson.iteritems():
            if key in key_counts:
                key_counts[key] += 1
            else:
                key_counts[key] = 1
            if key in key_values:
                if value not in key_values[key]:
                    key_values[key].append(value)
            else:
                key_values[key] = [value]

print json.dumps(key_counts, sort_keys=True, indent=4)
print json.dumps(key_values, sort_keys=True, indent=4)
