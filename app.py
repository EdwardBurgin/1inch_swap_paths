from flask import Flask, flash, redirect, render_template

from one_inch_swap_path import compose_swap_path_from_tx_hash, \
  one_inch_contract_address, one_inch_proxy_address, oneinch_exchange

from pprint import pprint

import simplejson as json

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('swap_paths.html', 
      tx_hash='',
      swap_path='', 
      nodes=json.dumps([]), 
      links=json.dumps([]))

@app.route('/<string:tx_hash>/')
def getSwapPath(tx_hash):
    swap_path = compose_swap_path_from_tx_hash(tx_hash)

    node_addresses = []
    links = []
    # pprint(swap_path)

    node_addresses.append(swap_path['sender_address'])
    node_addresses.append(one_inch_contract_address)
    node_addresses.append(one_inch_proxy_address)
    
    for tx in swap_path['starting_transactions']:

      if tx['from'] not in node_addresses:
        node_addresses.append(tx['from'])
      if tx['to'] not in node_addresses:
        node_addresses.append(tx['to'])

      text = ''
      if tx.__contains__('printableValue'):
        text = str(tx['printableValue']) + ' ' + tx['printableSymbol']

      links.append({
        'from':tx['from'], 
        'to':tx['to'],
        'text': text})

    for path in swap_path['paths']:
      t = 0
      prev_to = path['transactions'][0]['from']
      for transaction in path['transactions']:
        to_add = transaction['to']
        from_add = prev_to
        if to_add == one_inch_proxy_address \
          and len(path['transactions']) - 1 == t:
          to_add = transaction['to']+' '
        else:
          to_add = transaction['to']+' '+str(t)

        if from_add not in node_addresses:
          node_addresses.append(from_add)

        if to_add not in node_addresses:
          node_addresses.append(to_add)
        
        # if transaction['contractAddress'] != '':
        #   node_addresses.append(transaction['contractAddress'])

        text = ''
        if transaction.__contains__('printableValue'):
          text = str(transaction['printableValue']) + ' ' + transaction['printableSymbol']

        links.append({
          'text': text,
          'from':from_add, 
          'to': to_add})

        prev_to = to_add
        t = t + 1

    for tx in swap_path['ending_transactions']:
      to_add = tx['to']
      from_add = tx['from']
      if to_add in [one_inch_proxy_address, \
        one_inch_contract_address, swap_path['sender_address']]:
        to_add = tx['to']+' '
      if from_add in [one_inch_proxy_address, \
        one_inch_contract_address, swap_path['sender_address']]:
        from_add = tx['from']+' '

      if from_add not in node_addresses:
        node_addresses.append(from_add)

      if to_add not in node_addresses:
        node_addresses.append(to_add)

      source = ''
      if oneinch_exchange.tokens_by_address.__contains__(tx['contractAddress']):
        source = oneinch_exchange.tokens_by_address[tx['contractAddress']]['logoURI']

      text = ''
      if tx.__contains__('printableValue'):
        text = str(tx['printableValue']) + ' ' + tx['printableSymbol']

      links.append({
        'from':from_add, 
        'to':to_add,
        'text': text})

    nodes = []
    for node in node_addresses:
      name = node[0: 20]+'...'
      key = node
      if node == swap_path['sender_address']:
        name = 'Sender'
        key = 'Sender'
      elif node == one_inch_contract_address:
        name = '1INCH'
        key = '1INCH'
      elif node == one_inch_proxy_address:
        name = '1INCH PROXY'
        key = '1INCH PROXY'
      elif node == swap_path['sender_address']+' ':
        name = 'Sender'+' '
        key = 'Sender'+' '
      elif node == one_inch_contract_address+' ':
        name = '1INCH'+' '
        key = '1INCH'+' '
      elif node == one_inch_proxy_address+' ':
        name = '1INCH PROXY'+' '
        key = '1INCH PROXY'+' '

      adv_node = dict(key=key, name=name)

      nodes.append(adv_node)

    for link in links:
      if link['from'] == swap_path['sender_address']:
        link['from'] = 'Sender'
      elif link['from'] == one_inch_contract_address:
        link['from'] = '1INCH'
      elif link['from'] == one_inch_proxy_address:
        link['from'] = '1INCH PROXY'
      if link['to'] == swap_path['sender_address']:
        link['to'] = 'Sender'
      elif link['to'] == one_inch_contract_address:
        link['to'] = '1INCH'
      elif link['to'] == one_inch_proxy_address:
        link['to'] = '1INCH PROXY'

      if link['from'] == swap_path['sender_address']+' ':
        link['from'] = 'Sender'+' '
      elif link['from'] == one_inch_contract_address+' ':
        link['from'] = '1INCH'+' '
      elif link['from'] == one_inch_proxy_address+' ':
        link['from'] = '1INCH PROXY'+' '
      if link['to'] == swap_path['sender_address']+' ':
        link['to'] = 'Sender'+' '
      elif link['to'] == one_inch_contract_address+' ':
        link['to'] = '1INCH'+' '
      elif link['to'] == one_inch_proxy_address+' ':
        link['to'] = '1INCH PROXY'+' '
    
    print('tx hash is {}'.format(tx_hash))
    return render_template('swap_paths.html', 
      tx_hash=json.dumps(dict(hash=tx_hash)), 
      swap_path=json.dumps(swap_path), 
      nodes=json.dumps(nodes), 
      links=json.dumps(links))


if __name__ == '__main__':
    app.run(debug=True)