# payload = "{\"name\": \"{name}\",\n\"surname\": \"{surname}\",\n\"room\": {room},\n\"chat_id\": {chat_id}}".format(name='Test4', surname='soid', room=333, chat_id=24142)
import requests

url = "http://127.0.0.1:5000/api/student?chat-id=241"

payload={}
files={}
headers = {}

response = requests.request("GET", url, headers=headers, data=payload, files=files).json()

print(response)
