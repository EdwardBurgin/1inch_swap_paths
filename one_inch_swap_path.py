"""1inch_swap_path.py"""
import json
import requests
from pprint import pprint
from decimal import Decimal
from utils import wei_to_eth, eth_to_wei
from oneinch_exchange import OneInchExchange
from etherscan import Etherscan

import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

"""
For the webapp, the user will input his/her ethereum address, 
and they will see all the transactions that happend via the 
1inch exchange, including the swap paths.

user can also input a specific tx hash, to see info about a specific tx

"""
weth_contract_address = '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'
one_inch_contract_address = '0x11111254369792b2ca5d084ab5eea397ca8fa48b'
one_inch_proxy_address = '0x728bbe9bbee3af78ad611315076621865950b344' 

one_inch_contracts = ['0x69fb8c626bc66ac5c6282768b96cd9fabe60efb8', 
  one_inch_proxy_address, one_inch_contract_address]

api_key = os.environ.get('ETHERSCAN_API_KEY')

test_txs = [
'0x2f2484a81f79ad4bba3be406c2193ccfce0a071167a6853baf39d31ade693eee',
'0xb1d4da322012feebc45012b94182a8c1d294e1e123c261ef02349aa586031a9c',
'0x62d1dece34e9d06a86e61542e76983e12f8f7c38f54dfe2aa44725772822aab7',
'0x9ff1185d01f96e101baddce30f1e8cba16a03b95340cc80d5f688063fd0fe67d',
'0x8d720401121afe4524bb7f6a9842af5cb347e19da9784bbc9419ec53eb563b29',
'0xcd4973f26a83da507c73846e65c97aea507e2aaa0634c612fe309ed48bc2bfcf',
'0xfd7165bfd6bbcfa30f1b75d9ea0d67e88b760bedcc39f6de487c9394ab69b56a']

test_tx_hash = test_txs[5]

etherscan_api = Etherscan(api_key)
oneinch_exchange = OneInchExchange(address='')

def compose_swap_path_from_tx_hash(tx_hash, sender_address=None, debug=False):

  # Get internal txs info
  internal_txs = []
  try:
    internal_txs = etherscan_api.get_internal_txs_by_txhash(tx_hash)
  except:
    print("No internal transactions.")

  tx_info = etherscan_api.get_proxy_transaction_by_hash(tx_hash)
  sender_address = tx_info['from']
  block_number = int(tx_info['blockNumber'][2:], 16)
  total_eth_amount = Decimal(int(tx_info['value'][2:], 16))

  internal_transactions = []
  
  # Get internal token transfers (only those relating tot this swap)
  all_token_transfers = etherscan_api.get_erc20_token_transfer_events_by_address(
    address=one_inch_proxy_address, startblock=block_number, 
    endblock=block_number, sort='asc')

  internal_token_transfers = [tkn_tsf for tkn_tsf in all_token_transfers \
    if tkn_tsf['hash'] == tx_hash]

  all_user_token_transfers = etherscan_api.get_erc20_token_transfer_events_by_address(
    address=sender_address, startblock=block_number, 
    endblock=block_number, sort='asc') 

  user_token_transfers = [tkn_tsf for tkn_tsf in all_user_token_transfers \
    if tkn_tsf['hash'] == tx_hash]

  internal_token_transfers.extend(user_token_transfers)
  all_tsfs_txs = internal_txs
  all_tsfs_txs.extend(internal_token_transfers)

  for txn in all_tsfs_txs:
    start_symbol = 'ETH'
    start_value = wei_to_eth(txn['value'])

    if txn.__contains__('tokenSymbol'):
      start_symbol = txn['tokenSymbol']
      decimals = int(txn['tokenDecimal'])
      start_value = Decimal(txn['value']) / Decimal(10**decimals)
    elif oneinch_exchange.tokens_by_address.__contains__(txn['to']):
      tkn_info = oneinch_exchange.tokens_by_address[txn['to']]
      # pprint(tkn_info)
      start_symbol = tkn_info['symbol']
      decimals = int(tkn_info['decimals'])
      start_value = Decimal(txn['value']) / Decimal(10**decimals)

    txn['printableValue'] = round(start_value, 4)
    txn['printableSymbol'] = start_symbol
    # print(txn['printableValue'],  txn['printableSymbol'])

  if debug:
    pprint(all_tsfs_txs)
    print('Found {} transactions'.format(len(all_tsfs_txs)))
    print('Sender Address: {}'.format(sender_address))

  pre_transactions = []

  # Get the absolue first transactions (FROM SENDER TO 1INCH)
  pre_starting_tx = None
  pre_starting_txs = [tx for tx in all_tsfs_txs \
    if tx['from'] == sender_address \
    and tx['to'] == one_inch_contract_address]
  if len(pre_starting_txs) > 0:
    pre_starting_tx = pre_starting_txs[0]
  else:
    pre_starting_tx = tx_info

  pre_transactions.append(pre_starting_tx)

  # Get the first transactions (FROM 1INCH TO 1INCH PROXY)
  starting_tx = None
  order_type = 'ETH_ORDER'
  starting_tx = [tx for tx in all_tsfs_txs \
    if tx['from'] == one_inch_contract_address \
    and tx['to'] != sender_address][0]
  if total_eth_amount == Decimal(0):
    order_type = 'TOKEN_ORDER'
    assert starting_tx.__contains__('tokenName')
  else:
    assert not starting_tx.__contains__('tokenName')
    assert Decimal(starting_tx['value']) == total_eth_amount

  pre_transactions.append(starting_tx)
  used_txs = [pre_starting_tx, starting_tx]

  if debug:
    print('Starting Tx:')
    pprint(starting_tx)

  starting_token_address = starting_tx['contractAddress']

  next_txs = [tx for tx in all_tsfs_txs \
      if tx['from'] == starting_tx['to'] \
      and tx['to'] not in \
        [sender_address, one_inch_contract_address] \
      and not tx.__contains__('tokenName')] \
    if order_type == 'ETH_ORDER' \
    else [tx for tx in internal_token_transfers \
      if tx['from'] == starting_tx['to'] \
      and tx['to'] not in \
        [sender_address, one_inch_contract_address] \
      and tx['contractAddress'] == starting_token_address \
      and tx.__contains__('tokenName')]

  if debug:
    print('len {}'.format(len(next_txs)))
    pprint(next_txs[0])

  intermediary_tx = None
  if len(next_txs) == 1 and next_txs[0]['to'] == weth_contract_address:
    if debug:
      print('intermediary_tx')

    intermediary_tx = next_txs[0]
    pre_transactions.append(intermediary_tx)
    used_txs.append(intermediary_tx)
    next_txs = [tx for tx in all_tsfs_txs \
      if tx['from'] == intermediary_tx['from'] \
      and tx['to'] not in [sender_address, one_inch_contract_address] \
      and tx['contractAddress'] == weth_contract_address]

  if debug:
    print('Next txs')
    pprint(next_txs)

  for tx in next_txs:
    found_match = False
    if tx['to'] in one_inch_contracts or tx['to'] == weth_contract_address:
      continue

    for tx2 in all_tsfs_txs:
      if tx != tx2:
        if tx['to'] == tx2['from']:
          found_match = True
          break
    if not found_match:

      if debug:
        print('Couldn\'t find a match for: ')
        pprint(tx)
      all_inerim_token_transfers = etherscan_api.get_erc20_token_transfer_events_by_address(
        address=tx['to'], startblock=block_number, 
        endblock=block_number, sort='asc') 
      interim_token_transfers = [tkn_tsf for tkn_tsf in all_inerim_token_transfers \
        if tkn_tsf['hash'] == tx_hash]

      all_tsfs_txs.extend(interim_token_transfers)

  destination_token_address = \
    user_token_transfers[len(user_token_transfers)-1]['contractAddress']\
    if order_type == 'ETH_ORDER' else None

  paths = []
  used_txs.extend(next_txs.copy())

  for n_tx in next_txs:
    path = dict(transactions=[n_tx])

    next_ntxs = [tx for tx in all_tsfs_txs \
      if (tx['from'] == n_tx['to'] or \
        tx['contractAddress'] == n_tx['to']) \
      and tx['value'] == n_tx['value'] \
      and tx not in used_txs]

    if len(next_ntxs) == 0 and n_tx.__contains__('tokenName'):
      next_ntxs = [tx for tx in all_tsfs_txs \
        if tx['from'] == n_tx['to'] \
        and tx not in used_txs \
        and tx.__contains__('tokenName')]

      if len(next_ntxs) == 0 \
        and n_tx['to'] != one_inch_proxy_address:
        next_ntxs = [tx for tx in all_tsfs_txs \
          if tx['from'] == n_tx['to'] \
          and tx not in used_txs]

    while len(next_ntxs) > 0:
      prev_one = next_ntxs[0]

      path['transactions'].append(prev_one)
      used_txs.append(prev_one)

      next_ntxs = [tx for tx in all_tsfs_txs \
        if (tx['from'] == prev_one['to'] or \
          tx['contractAddress'] == n_tx['to']) \
        and tx['value'] == prev_one['value']\
        and tx not in used_txs]

      if len(next_ntxs) == 0:
        next_ntxs = [tx for tx in all_tsfs_txs \
          if tx['from'] == prev_one['to'] \
          and tx not in used_txs \
          and tx.__contains__('tokenName')]

        if len(next_ntxs) == 0:
          if prev_one['to'] != one_inch_proxy_address:
            next_ntxs = [tx for tx in all_tsfs_txs \
              if tx['from'] == prev_one['to'] \
              and tx not in used_txs]

      if prev_one['contractAddress'] == destination_token_address:
        break

    paths.append(path)

  if debug:
    print('\nPaths:')
    pprint(paths)
    print('Destination address is {}'.format(destination_token_address))

  # print('At the end, balances are:')

  balances = dict()
  for path in paths:
    last_tx = path['transactions'][len(path['transactions'])-1] 
    if last_tx.__contains__('tokenSymbol'):
      if balances.__contains__(last_tx['to']):
        if balances[last_tx['to']].__contains__(last_tx['tokenSymbol']):
          balances[last_tx['to']][last_tx['tokenSymbol']] += Decimal(last_tx['value'])
        else:
          balances[last_tx['to']][last_tx['tokenSymbol']] = Decimal(last_tx['value'])
      else:
        balances[last_tx['to']] = dict()
        balances[last_tx['to']][last_tx['tokenSymbol']] = Decimal(last_tx['value'])

  # pprint(balances)

  # for add in balances.keys():
  #   if add != one_inch_proxy_address:
  #     for path in paths:
  #       last_tx = path['transactions'][len(path['transactions'])-1]

  ending_txs = []

  current_from = one_inch_proxy_address

  for txn in all_tsfs_txs:
    if txn not in used_txs:
      # if txn['from'] == current_from:
      ending_txs.append(txn)
      used_txs.append(txn)
        # current_from = txn['to']

  return dict(
    pre_starting_tx=pre_starting_tx,
    starting_tx=starting_tx,
    intermediary_tx=intermediary_tx,
    starting_transactions=pre_transactions,
    ending_transactions=ending_txs,
    sender_address=sender_address,
    destination_token_address=destination_token_address,
    order_type=order_type,
    total_eth_amount=total_eth_amount,
    all_tsfs_txs=all_tsfs_txs,
    balances=balances,
    paths=paths)


def get_printable_path(path_dict):

  start_symbol = 'ETH'
  start_value = wei_to_eth(path_dict['total_eth_amount'])
  if path_dict['order_type'] == 'TOKEN_ORDER':
    starting_tx = path_dict['starting_tx']
    start_symbol = starting_tx['tokenSymbol']
    decimals = int(starting_tx['tokenDecimal'])
    start_value = Decimal(starting_tx['value']) / Decimal(10**decimals)

  starting_text = '\nStart with {} {} '.format(start_symbol, start_value)
  if path_dict['intermediary_tx'] != None:
    intermediary_tx = path_dict['intermediary_tx']
    inter_symbol = 'ETH'
    inter_value = wei_to_eth(intermediary_tx['value'])
    if intermediary_tx.__contains__('tokenSymbol'):
      inter_symbol = intermediary_tx['tokenSymbol']
      decimals = int(intermediary_tx['tokenDecimal'])
      inter_value = Decimal(intermediary_tx['value'])/Decimal(10**decimals)
    elif intermediary_tx['to'] in [weth_contract_address]:
      inter_symbol = 'WETH'

    starting_text = starting_text + '-> {} {} '.format(inter_value, inter_symbol)

  for path in path_dict['paths']:
    text = '\n| '
    prev_symbol = None
    for tx in path['transactions']:
      # if prev_symbol != tx['tokenSymbol']:
      decimals = 18
      symbol = 'ETH'
      if tx.__contains__('tokenSymbol'):
        decimals = int(tx['tokenDecimal'])
        symbol = tx['tokenSymbol']

      val = Decimal(tx['value'])/Decimal(10**decimals)
      text = text + "-> {} {} ".format(str(val), symbol)
      # if tx['type'] == 'fee':
      #   text = text + '(fee) '
      prev_symbol = symbol

    starting_text += text

  return starting_text

if __name__ == '__main__':
  for tx_hash in test_txs[:]: 
    path = compose_swap_path_from_tx_hash(tx_hash, None, False)
    print(get_printable_path(path))
    pprint(path['balances'])
    pprint(path)
    print()

