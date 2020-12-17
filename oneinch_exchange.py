import json
import requests
from decimal import Decimal

class OneInchExchange:

  base_url = "https://api.1inch.exchange/"

  versions = dict(
    v2 = "v2.0/"
  )

  endpoints = dict(
    swap = "swap",
    quote = "quote"
  )

  tokens = dict()
  tokens_by_address = dict()
  protocols = []

  def __init__(self, address):
    self._get_tokens()
    self._get_protocols()
    self.address = address

  def _get(self, url, params=None, headers=None):
    """ Implements a get request """
    try:
      response = requests.get(url, params=params, headers=headers)
      payload = json.loads(response.text)
      data = payload
    except requests.exceptions.ConnectionError as e:
      print("ConnectionError when trying to GET from "+url)
      data = None # dict(url=url, msg=e, success=False, params=params)
    return data

  def _health_check(self):
    url = "https://api.1inch.exchange/v2.0/healthcheck"
    response = requests.get(url)
    result = json.loads(response.text)
    if not result.__contains__('status'):
      raise Exception("Did not get expected result from API call, '\
        'was expecting the result to contain the word `status`.")

    return result['status']

  def _get_tokens(self):
    url = "https://api.1inch.exchange/v2.0/tokens"
    # response = requests.get(url)
    # result = json.loads(response.text)

    result = self._get(url)

    if not result.__contains__('tokens'):
      # raise Exception("Did not get expected result from API call, '\
      #   'was expecting the result to contain the word `tokens`.")
      return

    for key in result['tokens']:
      self.tokens_by_address[key] = result['tokens'][key]
      self.tokens[result['tokens'][key]['symbol']] = result['tokens'][key]

  def _get_protocols(self):
    url = "https://api.1inch.exchange/v2.0/protocols"
    # response = requests.get(url)
    # result = json.loads(response.text)
    result = self._get(url)

    if not result.__contains__('protocols'):
      # raise Exception("Did not get expected result from API call, '\
      #   'was expecting the result to contain the word `protocols`.")
      return

    self.protocols = result

  def get_quote(self, from_token:str, to_token:str, amount:int):
    url = self.base_url + self.versions['v2'] + self.endpoints['quote']
    url = url + "?fromTokenAddress={}&toTokenAddress={}&amount={}".format(
        self.tokens[from_token]['address'], 
        self.tokens[to_token]['address'], 
        format(Decimal(10**self.tokens[from_token]['decimals'] * amount)\
          .quantize(Decimal('1.')), 'n')
      )
    result = self._get(url)
    return result

  def do_swap(self, from_token:str, to_token:str, amount:int, from_address:str, slippage:int):
    url = self.base_url + self.versions['v2'] + self.endpoints['quote']
    url = url + "?fromTokenAddress={}&toTokenAddress={}&amount={}".format(
        self.tokens[from_token]['address'], 
        self.tokens[to_token]['address'], 
        amount)
    url = url + "&fromAddress={}&slippage={}".format(
        from_address, slippage)
    result = self._get(url)
    return result