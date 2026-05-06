import csv
import os
import requests
from datetime import datetime, timedelta

SERPAPI_KEY = os.environ.get("SERPAPI_KEY")

ROUTES_FILE = "routes.csv"

def date_after(days):
    return (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

def fetch_price(origin, destination, outbound_date):

    params = {
        "engine": "google_flights",
        "departure_id": origin,
        "arrival_id": destination,
        "outbound_date": outbound_date,
        "type": "2",
        "currency": "JPY",
        "hl": "ja",
        "api_key": SERPAPI_KEY
    }

    response = requests.get(
        "https://serpapi.com/search",
        params=params,
        timeout=60
    )

    data = response.json()

    flights = data.get("best_flights", [])

    if not flights:
        return {
            "price": "",
            "airline": "",
            "status": "NO_RESULT"
        }

    first = flights[0]

    return {
        "price": first.get("price", ""),
        "airline": first.get("flights", [{}])[0].get("airline", ""),
        "status": "OK"
    }

def main():

    today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    departure_date = date_after(30)

    output_rows = []

    with open(ROUTES_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:

            if row["active"] != "TRUE":
                continue

            result = fetch_price(
                row["origin"],
                row["destination"],
                departure_date
            )

            output_rows.append({
                "check_date": today,
                "direction": row["direction"],
                "origin": row["origin"],
                "destination": row["destination"],
                "market": row["market"],
                "purpose": row["purpose"],
                "departure_date": departure_date,
                "airline": result["airline"],
                "price": result["price"],
                "status": result["status"]
            })

    output_file = f"fare_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    with open(output_file, "w", newline="", encoding="utf-8-sig") as f:

        fieldnames = [
            "check_date",
            "direction",
            "origin",
            "destination",
            "market",
            "purpose",
            "departure_date",
            "airline",
            "price",
            "status"
        ]

        writer = csv.DictWriter(f, fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(output_rows)

    print(f"saved: {output_file}")

if __name__ == "__main__":
    main()
