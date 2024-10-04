import os
from datetime import datetime, timedelta
import json
import random
from itertools import product
from dotenv import load_dotenv
import metronome
from metronome import Metronome

# load env variables
load_dotenv()

#### INPUTS #####
INPUT_FILE_NAME="config.json"
OUTPUT_FILE_NAME='output.json'
DELTA_DAYS_SINCE_RATES_ENABLED=35

#### PARAMETERS #####
START_DATE = datetime.today().date() - timedelta(days=DELTA_DAYS_SINCE_RATES_ENABLED)
START_DATE_UTC = (START_DATE).strftime('%Y-%m-%dT00:00:00+00:00')  
CONFIG = json.load(open(INPUT_FILE_NAME))
client = Metronome(
    bearer_token=os.environ.get("METRONOME_BEARER_TOKEN"),
    max_retries=2, # default is 2
    timeout=20.0, # default is 60
)

def main():
    output = { "rate_card_id" : None, "customer_id":[], "contract_id":[], "pricing_and_packaging": CONFIG["pricing_and_packaging"] }
    
    output["pricing_and_packaging"] = create_billable_metric(output["pricing_and_packaging"])
    updateOutputFile(output)
    
    output["pricing_and_packaging"] = create_products(output["pricing_and_packaging"])
    updateOutputFile(output)
    
    output["rate_card_id"] = create_rate_card(name=CONFIG["rate_card"]["name"])
    updateOutputFile(output)

    add_rates(output["rate_card_id"], output["pricing_and_packaging"])


# 1. CREATE BILLABLE METRICS
def create_billable_metric(pricing_and_packaging):
    for idx, p in enumerate(pricing_and_packaging):
        if 'billable_metric' in p:
            try:
                payload = build_billable_metric_payload(p["billable_metric"], p["product"]) 
                result = json.loads(
                    client.billable_metrics.create(** payload).to_json()
                )
                pricing_and_packaging[idx].update({
                    "metronome_metric_id": result["data"]["id"]
                })
                print(f'SUCCESS - create billable metrics: {pricing_and_packaging[idx]["metronome_metric_id"]}')
            except metronome.APIConnectionError as e:
                print(f'ERROR - create billable metrics {p["billable_metric"]["name"]}: the server could not be reached')
            except metronome.RateLimitError as e:
                print(f"ERROR - create billable metrics {p["billable_metric"]["name"]}: 429 rate limit error.")
            except metronome.APIStatusError as e:
                print(f"ERROR - create billable metrics {p["billable_metric"]["name"]}: {e.status_code} - {e.response}")
        else: 
            break
    return pricing_and_packaging

# 2. CREATE PRODUCTS
def create_products(pricing_and_packaging):
    for idx, p in enumerate(pricing_and_packaging):
        try: 
            payload = build_product_payload(p["product"], p["metronome_metric_id"] if "metronome_metric_id" in p else None)
            result = json.loads(
                client.contracts.products.create(** payload).to_json()
            )
            pricing_and_packaging[idx].update({
                "metronome_product_id":  result["data"]["id"]
            })
            print(f'SUCCESS - product created {p["product"]["name"]}')
        except metronome.APIConnectionError as e:
            print(f'ERROR - create product {p["product"]["name"]}: the server could not be reached')
        except metronome.RateLimitError as e:
            print(f"ERROR - create product {p["product"]["name"]}: 429 rate limit error.")
        except metronome.APIStatusError as e:
            print(f"ERROR - create product {p["product"]["name"]}: {e.status_code} - {e.response}")
    return pricing_and_packaging
    

# 3. CREATE A RATE CARD
def create_rate_card(name):
    try:
        response = json.loads(
            client.contracts.rate_cards.create(name=name).to_json()
        )
        print(f'SUCCESS - create rate card {response['data']['id']}')
        return response['data']['id']
    except metronome.APIConnectionError as e:
        print(f'ERROR - create rate_card {name}: the server could not be reached')
    except metronome.RateLimitError as e:
        print(f"ERROR - create rate_card {name}: 429 rate limit error.")
    except metronome.APIStatusError as e:
        print(f"ERROR - create rate_card {name}: {e.status_code} - {e.response}")

# 4. ADD RATES
def add_rates(rate_card_id, pricing_and_packaging):
    try:
        client.contracts.rate_cards.rates.add_many(
            rate_card_id=rate_card_id,
            rates=build_rates_payload(pricing_and_packaging)
        )
        print(f'SUCCESS - added rates to the rate card.')
    except metronome.APIConnectionError as e:
        print(f'ERROR - add rates: the server could not be reached')
    except metronome.RateLimitError as e:
        print(f"ERROR - add rates: 429 rate limit error.")
    except metronome.APIStatusError as e:
        print(f"ERROR - add rates: {e.status_code} - {e.response}")

def updateOutputFile(data):
    with open(OUTPUT_FILE_NAME, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def build_billable_metric_payload(billable_metric, product):
    property_filters = [{
        "name": billable_metric["metric_key"],
        "exists":True,
    }]
    for p in billable_metric["properties"]:
        property = {
            "name": p["name"],
            "exists": True
        }
        if p["enum"] == True:
            property.update({"in_values" : p["in_values"]})
        property_filters.append(property)

    return {
        "name": billable_metric["name"],
        "event_type_filter": {
            "in_values": [billable_metric["event_type"]]
        },
        "property_filters":property_filters,
        "aggregation_type": billable_metric["metric_agg_rule"],
        "aggregation_key":billable_metric["metric_key"],
        "group_keys": [ product["pricing_group_key"] + list(set(product["presentation_group_key"]) - set(product["pricing_group_key"])) ]
    }
    
def build_product_payload(product, billable_metric_id):
    if product["type"] == "USAGE":
        product.update({
            "billable_metric_id": billable_metric_id
        })
    return product

def build_rates_payload(pricing_and_packaging):
    rates=[]
    for p in pricing_and_packaging:
        if p["product"]["type"] == "USAGE" and "metronome_product_id" in p: # ignoring subscription or fixed products 
            if len(p["product"]["pricing_group_key"]) > 0:
                pricing_group_values = {}
                for key in p["product"]["pricing_group_key"]:
                    pricing_group_values[key] = [item for item in p["billable_metric"]["properties"] if item.get('name') == key][0]["in_values"]
                keys, values = zip(*pricing_group_values.items())
                combinations = [dict(zip(keys, p)) for p in product(*values)]
                for c in combinations:
                    rates.append({
                        "product_id": p["metronome_product_id"],
                        "starting_at": START_DATE_UTC  ,
                        "entitled": p["pricing"]["entitled"],
                        "rate_type": "FLAT",
                        "price": round(random.uniform( p["pricing"]["pricing_in_cents"]["min"], p["pricing"]["pricing_in_cents"]["max"]), p["pricing"]["pricing_in_cents"]["round"]-2),
                        "pricing_group_values": c
                    })
            else:
                rates.append({
                    "product_id": p["metronome_product_id"],
                    "starting_at": START_DATE_UTC  ,
                    "entitled": True,
                    "rate_type": "FLAT",
                    "price": round(random.uniform( 10, 60), 2)
                })
    return rates

main()