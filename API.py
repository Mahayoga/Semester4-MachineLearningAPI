from flask import Flask
from flask import request
from pymongo import MongoClient
from flask import render_template
from markupsafe import escape

app = Flask(__name__)
client = MongoClient('mongodb://localhost:27017/')
db = client['diabetes_db']
collection = db['user']

# Website Login
@app.route('/login', methods=['POST'])
def login():
    result = collection.find_one(
        {
            'email': request.json['email'], 'password': request.json['password']
        }
    )
    if result != None:
        return {
            'status': 'success',
            'data_user': {
                'id_user': str(result['_id']),
                'nama_depan': result['nama_depan'],
                'nama_belakang': result['nama_belakang'],
                'role': result['role'],
                'email': result['email']
            }
        }
    else:
        return {
            'status': 'error',
            'msg': 'Email atau Password salah!'
        }
    

@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.json
        res = collection.insert_one({
            'nama_depan': data['nama_depan'],
            'nama_belakang': data['nama_belakang'],
            'role': data['role'],
            'email': data['email']
        })
        result = collection.find_one(
            {
                '_id': res.inserted_id
            }
        )
        print(result)
        return {
            'status': 'success',
            'data_user': {
                'id_user': str(result['_id']),
                'nama_depan': result['nama_depan'],
                'nama_belakang': result['nama_belakang'],
                'role': result['role'],
                'email': result['email']
            }
        }
    except:
        return {
            'status': 'error',
            'msg': 'Terjadi kesalahan!'
        }