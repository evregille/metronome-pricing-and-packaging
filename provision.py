import os
from datetime import datetime, timedelta
import json
import uuid
import random
from dotenv import load_dotenv
import metronome
from metronome import Metronome

# load env variables
load_dotenv()

#### INPUTS #####
INPUT_FILE_NAME="config.json"
OUTPUT_FILE_NAME='output.json'

DELTA_DAYS_SINCE_CONTRACT_START=35
CONTRACT_DURATION_YEARS=1

#### PARAMETERS #####
START_DATE = datetime.today().date() - timedelta(days=DELTA_DAYS_SINCE_CONTRACT_START)
START_DATE_UTC = (START_DATE).strftime('%Y-%m-%dT00:00:00+00:00')  
MID_CONTRACT_UTC = (START_DATE + timedelta(days=CONTRACT_DURATION_YEARS*365-180)).strftime('%Y-%m-%d')+ 'T00:00:00+00:00'
CONTRACT_END_UTC = (START_DATE + timedelta(days=CONTRACT_DURATION_YEARS*365)).strftime('%Y-%m-%d')+ 'T08:00:00+00:00'

CONFIG = json.load(open(INPUT_FILE_NAME))
client = Metronome(
    bearer_token=os.environ.get("METRONOME_BEARER_TOKEN"),
    max_retries=2, # default is 2
    timeout=20.0, # default is 60
)

def main():
    f = open(OUTPUT_FILE_NAME)
    output = json.load(f)
    
    # for p in CONFIG["pricing_and_packaging"]:
    #     if p["product"]["type"] == "USAGE":
    #         send_events(CONFIG["customer"]["alias"], p["billable_metric"])

    customer_id = create_customer(CONFIG["customer"])
    output["customer_id"].append(customer_id)
    updateOutputFile(output)

    contract_id = create_contract(customer_id, output["rate_card_id"])
    output["contract_id"].append(contract_id)
    updateOutputFile(output)


# 1. SEND EVENTS
def send_events(alias, billable_metric):
    i=0
    events=[]
    while i < 100:
        e = {
            "transaction_id": str(uuid.uuid4()),
            "customer_id": alias,
            "event_type": billable_metric["event_type"],
            "timestamp": (datetime.today().date() - timedelta(days=random.randint(0, 32))).strftime('%Y-%m-%dT00:00:00+00:00'),
            "properties":{}
        }
        for property in billable_metric["properties"]:
            e["properties"][property["name"]] = random.choice(property["in_values"])
        e["properties"][billable_metric["metric_key"]] = round(random.uniform(billable_metric["metric_values"]["min"], billable_metric["metric_values"]["max"]), billable_metric["metric_values"]["round"])
        events.append(e)
        i=i+1
    try:
        client.usage.ingest(usage=events)
    except metronome.APIConnectionError as e:
        print(f'ERROR - ingest: the server could not be reached')
    except metronome.RateLimitError as e:
        print(f"ERROR - ingest: 429 rate limit error.")
    except metronome.APIStatusError as e:
        print(f"ERROR - ingest: {e.status_code} - {e.response}")

# 2. PROVISION CUSTOMER
def create_customer(customer):
    payload={
        "name": customer["name"],
        "ingest_aliases": customer["alias"],
        "billing_config": {
            "billing_provider_type": "stripe",
            "billing_provider_customer_id": customer["stripe_id"],
            "stripe_collection_method": "charge_automatically"
        } if "stripe_id" in customer else None
    }
    print(payload)
    try:
        response = json.loads(
            client.customers.create(** payload).to_json()
        )
        print(f'SUCCESS - create customer {response["data"]["id"]}')
    except metronome.APIConnectionError as e:
        print(f'ERROR - create customer: the server could not be reached')
    except metronome.RateLimitError as e:
        print(f"ERROR - create customer: 429 rate limit error.")
    except metronome.APIStatusError as e:
        print(f"ERROR - create customer: {e.status_code} - {e.response}")
    return response["data"]["id"]

# 3. CREATE CONTRACTS
def create_contract(customer_id, rate_card_id):
    payload={
        "customer_id": customer_id,
        "starting_at": START_DATE_UTC,
        "rate_card_id": rate_card_id
    }
    try:
        response = json.loads(
            client.contracts.create(** payload).to_json()
        )
        print(f'SUCCESS - create contract {response["data"]["id"]}')
    except metronome.APIConnectionError as e:
        print(f'ERROR - create contract: the server could not be reached')
    except metronome.RateLimitError as e:
        print(f"ERROR - create contract: 429 rate limit error.")
    except metronome.APIStatusError as e:
        print(f"ERROR - create contract: {e.status_code} - {e.response}")
    return response["data"]["id"]

def updateOutputFile(data):
    with open(OUTPUT_FILE_NAME, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

main()