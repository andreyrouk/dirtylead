import requests
import time
import csv
import os

# Config from environment variables
API_TOKEN = os.environ.get("APIFY_TOKEN")
ACTOR_ID = "scraperlink~google-maps-scraper"
SEARCH_QUERY = os.environ.get("SEARCH_QUERY", "residential cleaning service")
LOCATION = os.environ.get("LOCATION", "Austin, Texas, USA")
MAX_RESULTS = int(os.environ.get("MAX_RESULTS", 100))

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

# Step 1: Start the actor run
print(f"Starting scrape: '{SEARCH_QUERY}' in {LOCATION}...")
run_response = requests.post(
    f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs",
    headers=headers,
    json={
        "query": [f"{SEARCH_QUERY} in {LOCATION}"],
        "maxResults": MAX_RESULTS
    }
)

run_data = run_response.json()
run_id = run_data.get("data", {}).get("id")

if not run_id:
    print("Failed to start run. Response:", run_data)
    exit()

print(f"Run started. ID: {run_id}")
print("Waiting for results...")

# Step 2: Poll until finished
while True:
    status_response = requests.get(
        f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs/{run_id}",
        headers=headers
    )
    status = status_response.json().get("data", {}).get("status")
    print(f"Status: {status}")

    if status in ["SUCCEEDED", "FAILED", "ABORTED"]:
        break
    time.sleep(10)

if status != "SUCCEEDED":
    print(f"Run ended with status: {status}")
    exit()

# Step 3: Fetch results
print("Fetching results...")
dataset_id = status_response.json().get("data", {}).get("defaultDatasetId")
results_response = requests.get(
    f"https://api.apify.com/v2/datasets/{dataset_id}/items",
    headers=headers,
    params={"format": "json", "limit": MAX_RESULTS}
)

results = results_response.json()
print(f"Got {len(results)} results.")

# Debug: print all keys from first result to find name field
if results:
    print("Available fields in first result:", list(results[0].keys()))

# Step 4: Save to CSV - try multiple possible name fields
city = LOCATION.split(",")[0].strip().replace(" ", "_")
output_file = f"cleaning_leads_{city}.csv"
fields = ["name", "address", "phone", "website", "rating", "reviewCount", "category"]

with open(output_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for r in results:
        # Try multiple possible name field keys
        name = (
            r.get("name") or
            r.get("title") or
            r.get("placeName") or
            r.get("businessName") or
            r.get("placeTitle") or
            ""
        )
        writer.writerow({
            "name": name,
            "address": r.get("address") or r.get("fullAddress") or "",
            "phone": r.get("phone") or r.get("phoneNumber") or "",
            "website": r.get("website") or r.get("url") or "",
            "rating": r.get("rating") or r.get("stars") or "",
            "reviewCount": r.get("reviewCount") or r.get("reviews") or "",
            "category": r.get("category") or r.get("categories") or ""
        })

print(f"Saved to {output_file}")
