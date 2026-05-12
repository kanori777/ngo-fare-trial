import csv
import os
import requests
from datetime import datetime, timedelta

SERPAPI_KEY = os.environ.get("SERPAPI_KEY")
ROUTES_FILE = "routes.csv"

CABIN_CLASSES = [
    {"name": "Economy", "code": "1"},
    {"name": "Premium Economy", "code": "2"},
    {"name": "Business", "code": "3"},
]

def date_after(days=30):
    return (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

def fetch_flights(origin, destination, outbound_date, airline_code, cabin_class_name, cabin_class_code):
    params = {
        "engine": "google_flights",
        "departure_id": origin,
        "arrival_id": destination,
        "outbound_date": outbound_date,
        "type": "2",
        "travel_class": cabin_class_code,
        "currency": "JPY",
        "hl": "ja",
        "gl": "jp",
        "stops": "1",
        "include_airlines": airline_code,
        "api_key": SERPAPI_KEY
    }

    response = requests.get(
        "https://serpapi.com/search",
        params=params,
        timeout=60
    )

    data = response.json()

    flights = []
    flights.extend(data.get("best_flights", []))
    flights.extend(data.get("other_flights", []))

    rows = []

    for option in flights:
        price = option.get("price", "")
        total_duration = option.get("total_duration", "")
        legs = option.get("flights", [])

        # 直行便のみ採用
        if len(legs) != 1:
            continue

        leg = legs[0]
        airline = leg.get("airline", "")
        flight_number = leg.get("flight_number", "")

        # フィンエアー便のみ採用
        if (
            "AY" not in str(flight_number)
            and "フィンエアー" not in str(airline)
            and "Finnair" not in str(airline)
        ):
            continue

        rows.append({
            "cabin_class": cabin_class_name,
            "airline": airline,
            "flight_number": flight_number,
            "aircraft": leg.get("airplane", ""),
            "departure_airport": leg.get("departure_airport", {}).get("id", ""),
            "departure_time": leg.get("departure_airport", {}).get("time", ""),
            "arrival_airport": leg.get("arrival_airport", {}).get("id", ""),
            "arrival_time": leg.get("arrival_airport", {}).get("time", ""),
            "duration": leg.get("duration", total_duration),
            "price": price,
            "status": "OK"
        })

    if not rows:
        rows.append({
            "cabin_class": cabin_class_name,
            "airline": "",
            "flight_number": "",
            "aircraft": "",
            "departure_airport": origin,
            "departure_time": "",
            "arrival_airport": destination,
            "arrival_time": "",
            "duration": "",
            "price": "",
            "status": "NO_AY_DIRECT_RESULT"
        })

    return rows

def main():
    if not SERPAPI_KEY:
        raise RuntimeError("SERPAPI_KEY is not set")

    check_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    departure_date = date_after(30)

    output_rows = []

    with open(ROUTES_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            if row.get("active", "").upper() != "TRUE":
                continue

            for cabin in CABIN_CLASSES:
                flights = fetch_flights(
                    origin=row["origin"],
                    destination=row["destination"],
                    outbound_date=departure_date,
                    airline_code=row.get("airline_filter", "AY"),
                    cabin_class_name=cabin["name"],
                    cabin_class_code=cabin["code"]
                )

                for flight in flights:
                    output_rows.append({
                        "check_date": check_date,
                        "direction": row["direction"],
                        "origin": row["origin"],
                        "destination": row["destination"],
                        "market": row["market"],
                        "airport_group": row["airport_group"],
                        "purpose": row["purpose"],
                        "departure_date": departure_date,
                        "cabin_class": flight["cabin_class"],
                        "airline": flight["airline"],
                        "flight_number": flight["flight_number"],
                        "aircraft": flight["aircraft"],
                        "departure_airport": flight["departure_airport"],
                        "departure_time": flight["departure_time"],
                        "arrival_airport": flight["arrival_airport"],
                        "arrival_time": flight["arrival_time"],
                        "duration": flight["duration"],
                        "price": flight["price"],
                        "currency": "JPY",
                        "status": flight["status"],
                        "source": "SerpApi Google Flights API"
                    })

    output_file = f"ay_direct_fare_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    fieldnames = [
        "check_date",
        "direction",
        "origin",
        "destination",
        "market",
        "airport_group",
        "purpose",
        "departure_date",
        "cabin_class",
        "airline",
        "flight_number",
        "aircraft",
        "departure_airport",
        "departure_time",
        "arrival_airport",
        "arrival_time",
        "duration",
        "price",
        "currency",
        "status",
        "source"
    ]

    with open(output_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"saved: {output_file}")

if __name__ == "__main__":
    main()
