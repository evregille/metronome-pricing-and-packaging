# Metronome Pricing and Packaging

Collection of examples of scripts with [Metronome Python SDK](https://github.com/Metronome-Industries/metronome-python):
- deploy pricing and packaging as code on Metronome: it does simple configuration and you can adapt the scripts to your needs (looking at Metronome docs for available parameters)

- provision a customer with a contract: as for pricing and packaging, it does a simple flow and you can adapt the scripts to your business needs.

- clean-up all objects created

# How it works

## Configure
1. Set up your Metronome API KEY by creating an .env file where you provide the API KEY value

```bash
METRONOME_BEARER_TOKEN=YOUR_METRONOME_API_KEY
```

2. Define your different usage billable metrics, products and pricing in the `config.json` file.


## Setup your Pricing and Packaging
Script `setup.py` reads the `config.json` file to create your pricing stack with:
- billable metrics
- products
- rate card
- rates for each product and pricing group keys

```bash
python3 setup.py
```

## Provision a customer 
Script `provision.py` reads the `config.json` file to 
- create a customer object 
- send usage events (100 per billable metric)
- create a contract for the customer 

```bash
python3 provision.py
```

# Uninstall
You can clean-up the products and billable metrics as well as any customers created via the setup and provision script by running

```bash
python3 cleanup.py
```