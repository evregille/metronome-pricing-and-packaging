# What is it

Collection of default scripts to:
- deploy pricing and packaging as code on Metronome: it does simple configuration and you can adapt the scripts to your needs (looking at Metronome docs for available parameters)
- provision a customer with a contract: as for pricing and packaging, it does a simple flow and you can adapt the scripts to your business needs.
- clean-up all objects created

Those scripts are using Metronome Python SDK.

# How it works

Step 1: Configure
Set up your Metronome API KEY by creating an .env file with METRONOME_BEARER_TOKEN=YOUR API KEY

Define your different usage billable metrics, products and pricing in the `config.json` file.

Step 2: Setup your Pricing and Packaging

Run 
```python3 setup.py```

Step 3: Provision

Run 
```python3 provision.py```

# Uninstall
You can clean-up the products and billable metrics as well as any customers created via the setup and provision script by running

```python3 cleanup.py```