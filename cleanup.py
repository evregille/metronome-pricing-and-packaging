import os
import json
from dotenv import load_dotenv
import metronome
from metronome import Metronome

# load env variables
load_dotenv()

client = Metronome(
    bearer_token=os.environ.get("METRONOME_BEARER_TOKEN"),
    max_retries=2, # default is 2
    timeout=20.0, # default is 60
)

OUTPUT_FILE_NAME='output.json'

def main():
    f = open(OUTPUT_FILE_NAME)
    output = json.load(f)
    if "customer_id" in output and len(output["customer_id"]) > 0: 
        for customer in output["customer_id"]:
            archive_customer(customer)
        output["customer_id"]=[]
        output["contract_id"]=[]
        updateOutputFile(output)

    for idx, p in enumerate(output["pricing_and_packaging"]):
        if "metronome_product_id" in p:
            archive_product(p["metronome_product_id"])
            output["pricing_and_packaging"][idx]["metronome_product_id"] = None
        if "metronome_metric_id" in p:
            archive_billable_metric(p["metronome_metric_id"])
            output["pricing_and_packaging"][idx]["metronome_metric_id"] = None
    updateOutputFile(output)

def archive_customer(customer_id):
    client.customers.set_ingest_aliases(customer_id=customer_id, ** {
        "ingest_aliases": []
    })
    client.customers.archive(** {
        "id": customer_id
    })


def archive_product(product_id):
    client.contracts.products.archive(
        ** {
        "product_id": product_id
    })

def archive_billable_metric(metric_id):
    client.billable_metrics.archive(** {
        "id": metric_id
    })

def updateOutputFile(data):
    with open(OUTPUT_FILE_NAME, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

main() 

