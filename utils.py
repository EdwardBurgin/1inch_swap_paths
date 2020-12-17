from decimal import Decimal

def wei_to_eth(wei_value):
	return Decimal(wei_value) / Decimal(10**18)

def eth_to_wei(eth_value):
	return Decimal(eth_value) * Decimal(10**18)

def filter_dict_columns(dict_obj, callback):
    newDict = dict()
    # Iterate over all the items in dictionary
    for (key, value) in dict_obj.items():
        # Check if item satisfies the given condition then add to new dict
        if callback((key, value)):
            newDict[key] = value
    return newDict