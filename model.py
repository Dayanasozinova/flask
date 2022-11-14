import requests


response = requests.post('http://127.0.0.1:5000/user',
                         json={'title': 'Apple', 'description': 'about apple', 'owner': 'Dayana'}, )

response = requests.get('http://127.0.0.1:5000/user/2', )

print(response.status_code)
print(response.json())