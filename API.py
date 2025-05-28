import os
from dotenv import load_dotenv
import random as rd
import smtplib
from email.message import EmailMessage
from flask import Flask, jsonify
from flask_cors import CORS
from flask import request
from pymongo import MongoClient
from flask import render_template
from markupsafe import escape
import pymongo
from datetime import datetime, timezone

app = Flask(__name__)
CORS(app)
load_dotenv()
client = MongoClient('mongodb://localhost:27017/')
db = client['diabetes_db']
collectionUser = db['user']
collectionPasien = db['data_pasien']
collectionVerifikasi = db['verifikasi_email']

# Website Login
@app.route('/login', methods=['POST'])
def login():
    resultUser = collectionUser.find_one({
        'email': request.json['email'], 'password': request.json['password']
    })
    if resultUser != None:
        if resultUser['is_verified'] == False:
            return {
                'status': 'need_action',
                'msg': 'Email kamu sudah terdaftar, dan butuh verifikasi!'
            }
        resultPasien = collectionPasien.find_one({
            'id_user': resultUser['_id']
        })
        print(resultPasien)
        return {
            'status': 'success',
            'data_user': {
                'id_user': str(resultUser['_id']),
                'id_pasien': str(resultPasien['_id']),
                'nama_depan': resultPasien['nama_depan'],
                'nama_belakang': resultPasien['nama_belakang'],
                'tanggal_lahir': resultPasien['tanggal_lahir'],
                'umur': resultPasien['umur'],
                'gender': resultPasien['gender'],
                'alamat': resultPasien['alamat'],
                'role': resultUser['role'],
                'email': resultUser['email']
            }
        }
    else:
        return {
            'status': 'error',
            'msg': 'Email atau Password salah!'
        }
    
@app.route('/verifikasi-email', methods=['POST'])
def verifikasi_email():
    try:
        data = request.json
        if data['action'] == 'verification_email':
            kode_verifikasi = str(rd.randint(0, 9)) + str(rd.randint(0, 9)) + str(rd.randint(0, 9)) + str(rd.randint(0, 9)) + str(rd.randint(0, 9)) + str(rd.randint(0, 9))
            milisecond = int(datetime.now(timezone.utc).timestamp())
            res = collectionVerifikasi.find_one({
                'email': data['email'],
                'expired_at': {'$gt': milisecond}
            })

            if res == None:
                today = datetime.today()
                res = collectionVerifikasi.insert_one({  
                    'email': data['email'],
                    'kode': kode_verifikasi,
                    'created_at': datetime.now(timezone.utc),
                    'expired_at': datetime(today.year, today.month, today.day, today.hour + 1, today.minute, today.second).timestamp(),
                })
            else:
                kode_verifikasi = res['kode']
            
            kirim_pesan = EmailMessage()
            kirim_pesan['From'] = os.getenv("EMAIL_SENDER")
            kirim_pesan['To'] = data['email']
            kirim_pesan['Subject'] = "Kode Verifikasi | Reset Password | HealthDream App"

            html_content = f"""
                <!DOCTYPE html>
                <html lang="en">
                <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-EVSTQN3/azprG1Anm3QDgpJLIm9Nao0Yz1ztcQTwFspd3yD65VohhpuuCOmLASjC" crossorigin="anonymous">
                <title>Document</title>
                </head>
                <body>
                <div class="container-fluid">
                    <div class="container">
                    <div class="row justify-content-center p-4">
                        <div class="container border">
                        <div class="row">
                            <div class="col-md-12 bg-info">
                            <h4 class=" text-center p-4 text-white fw-4">HealthDream Verification Email</h4>
                            </div>
                            <div class="col-md-12 p-4">
                            <div class="row">
                                <div class="col-md-12 my-2">
                                Pengguna Aplikasi HealthDream,
                                </div>
                                <div class="col-md-12 my-2">
                                Kami menerima permintaan untuk memverifikasi email anda di aplikasi HealthDream. Untuk melanjutkan verifikasi, silahkan masukkan kode di bawah ini untuk melanjutkan. Berikut kode 6-digit anda:
                                </div>
                                <div class="col-md-12 my-2 text-center">
                                <h1>{kode_verifikasi}</h1>
                                </div>
                                <div class="col-md-12 my-2">
                                Anda menerima email ini karena anda melakukan permintaan daftar pada aplikasi kami yaitu HealthDream. Jika anda <b>tidak</b> melakukan pendaftaran di platform kami, <b>abaikan</b> email ini.
                                </div>
                            </div>
                            </div>
                        </div>
                        </div>
                    </div>
                    </div>
                </div>
                </body>
                </html>
            """

            kirim_pesan.add_alternative(html_content, subtype='html')
            # Mengirim email
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(os.getenv("EMAIL_SENDER"), os.getenv("EMAIL_PASSWORD"))
                server.send_message(kirim_pesan)
                print("Email berhasil dikirim!")
                print(kode_verifikasi)

            return {
                'status': 'success',
                'msg': 'Email berhasil dikirim!'
            }
        elif data['action'] == 'verification_email_code':
            milisecond = int(datetime.now(timezone.utc).timestamp())
            res = collectionVerifikasi.find_one({
                'email': data['email'],
                'expired_at': {'$gt': milisecond}
            })
            print(res['kode'])
            if res['kode'] == data['kode']:
                make_verification_complete = collectionUser.update_one({
                    'email': res['email']
                },
                {
                    '$set': {
                        'is_verified': True
                    }
                })
                return {
                    'status': 'success',
                    'msg': 'Email berhasil di verifikasi!'
                }
        return {
            'status': 'need_action',
            'msg': 'Email tidak ditemukan!'
        }
    except:
        return {
            'status': 'error',
            'msg': 'Kesalahan Server!'
        }

@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.json
        checkDataUser = collectionUser.find_one({
            'email': data['email']
        })

        if checkDataUser != None:
            if checkDataUser['is_verified'] == False:
                return {
                    'status': 'need_action',
                    'msg': 'Email kamu sudah terdaftar, dan butuh verifikasi!'
                }
            else:
                return {
                    'status': 'occupied',
                    'msg': 'Email sudah digunakan'
                }
        

        resUser = collectionUser.insert_one({
            'role': data['role'],
            'email': data['email'],
            'password': data['password'],
            'is_verified': False
        })
        resPasien = collectionPasien.insert_one({
            'nama_depan': data['nama_depan'],
            'nama_belakang': data['nama_belakang'],
            'tanggal_lahir': data['tanggal_lahir'],
            'umur': data['umur'],
            'gender': data['gender'],
            'alamat': data['alamat'],
            'id_user': resUser.inserted_id
        })
        resultPasien = collectionPasien.find_one({
            '_id': resPasien.inserted_id
        })
        resultUser = collectionUser.find_one({
            '_id': resUser.inserted_id
        })

        return {
            'status': 'success',
            'data_user': {
                'id_user': str(resultUser['_id']),
                'id_pasien': str(resultPasien['_id']),
                'nama_depan': resultPasien['nama_depan'],
                'nama_belakang': resultPasien['nama_belakang'],
                'tanggal_lahir': resultPasien['tanggal_lahir'],
                'umur': resultPasien['umur'],
                'gender': resultPasien['gender'],
                'alamat': resultPasien['alamat'],
                'role': resultUser['role'],
                'email': resultUser['email']
            }
        }
    except:
        return {
            'status': 'error',
            'msg': 'Terjadi kesalahan!'
        }
    
@app.route('/get/data-pasien', methods=['GET'])
def ambilDataUser():
    try:
        dataPasien = collectionPasien.find({})
        hasil = []
        for data in dataPasien:
            data['_id'] = str(data['_id'])
            hasil.append(data)

        return {
            'status': 'success',
            'data_pasien': hasil
        }
    except:
        return {
            'status': 'error',
            'msg': 'Terjadi kesalahan!'
        }
    
@app.route('/add/data-pasien', methods=['POST'])
def simpanDataUser():
    try:
        requestData = request.json
        insertData = collectionUser.insert_one({
            'nama_depan': requestData['nama_depan'],
            'nama_belakang': requestData['nama_belakang'],
            'umur': requestData['umur'],
            'jenis_kelamin': requestData['jenis_kelamin'],
            'alamat': requestData['alamat'],
            'role': 'user',
            'email': requestData['email'],
            'password': requestData['password'],
        })
        return {
            'status': 'success'
        }
    except:
        return {
            'status': 'error',
            'msg': 'Terjadi kesalahan!'
        }