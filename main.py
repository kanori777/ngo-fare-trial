import csv
import os
import requests
from datetime import datetime, timedelta

SERPAPI_KEY = os.environ.get("SERPAPI_KEY")
ROUTES_FILE = "routes.csv"

TARGET_WEEKS = [1, 4, 8]

TARGET_WEEKDAYS = [
    {"name": "Wednesday", "weekday": 2, "jp": "水"},
    {"name": "Friday", "weekday": 4, "jp": "金"},
]

CABIN_CLASSES = [
    {"name": "Economy", "code": "1"},
    {"name": "Premium Economy", "code": "2"},
    {"name": "Business", "code": "3"},
]

def target_date_for_weekday(weeks_ahead, target_weekday):
    today = datetime.now().date()
    base_date = today + timedelta(weeks=weeks_ahead)

    # Monday=0, Tuesday=1, Wednesday=2, ... Sunday=6
    monday_of_target_week = base_date - timedelta(days=base_date.weekday())
    target_date = monday_of_target_week + timedelta(days=target_weekday)

    return target_date.strftime("%Y-%m-%d")

def fetch_flights(
    origin,
    destination,
    outbound_date,
    airline_code,
    cabin_class_name,
    cabin_class_code,
    weeks_ahead,
    target_weekday_name,
    target_weekday_jp
):
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
            "weeks_ahead": weeks_ahead,
            "target_weekday": target_weekday_name,
            "departure_weekday": target_weekday_jp,
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
            "weeks_ahead": weeks_ahead,
            "target_weekday": target_weekday_name,
            "departure_weekday": target_weekday_jp,
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
    output_rows = []

    with open(ROUTES_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            if row.get("active", "").upper() != "TRUE":
                continue

            for weeks in TARGET_WEEKS:
                for weekday in TARGET_WEEKDAYS:
                    departure_date = target_date_for_weekday(
                        weeks_ahead=weeks,
                        target_weekday=weekday["weekday"]
                    )

                    for cabin in CABIN_CLASSES:
                        flights = fetch_flights(
                            origin=row["origin"],
                            destination=row["destination"],
                            outbound_date=departure_date,
                            airline_code=row.get("airline_filter", "AY"),
                            cabin_class_name=cabin["name"],
                            cabin_class_code=cabin["code"],
                            weeks_ahead=weeks,
                            target_weekday_name=weekday["name"],
                            target_weekday_jp=weekday["jp"]
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
                                "weeks_ahead": flight["weeks_ahead"],
                                "target_weekday": flight["target_weekday"],
                                "departure_date": departure_date,
                                "departure_weekday": flight["departure_weekday"],
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
        "weeks_ahead",
        "target_weekday",
        "departure_date",
        "departure_weekday",
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