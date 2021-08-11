import requests
from string import Template


def make_request(url, text, method='POST'):
  payload = text.