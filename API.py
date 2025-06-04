import os
from dotenv import load_dotenv
import numpy as np
import joblib
import random as rd
from bson import ObjectId
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
collectionHistori = db['histori']

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
        elif resultUser['username'] == '':
            return {
                'status': 'need_action_username',
                'msg': 'Kamu belum mendaftarkan username!'
            }
        resultPasien = collectionPasien.find_one({
            'id_user': resultUser['_id']
        })
        # print(resultPasien)
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
                'username': resultUser['username'],
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
    # try:
        data = request.json
        if data['action'] == 'verification_email':
            kode_verifikasi = str(rd.randint(0, 9)) + str(rd.randint(0, 9)) + str(rd.randint(0, 9)) + str(rd.randint(0, 9)) + str(rd.randint(0, 9)) + str(rd.randint(0, 9))
            milisecond = int(datetime.now(timezone.utc).timestamp())

            today = datetime.today()
            theMinute = today.minute
            theHour = today.hour
            if (today.minute + 10) >= 60:
                theMinute = (today.minute + 10) - 60
                if (today.hour + 1) >= 24:
                    theHour = 0
            else:
                theMinute += 10

            print(theMinute)
            print(theHour)
            res = collectionVerifikasi.insert_one({  
                'email': data['email'],
                'kode': kode_verifikasi,
                'created_at': datetime.now(timezone.utc),
                'expired_at': datetime(today.year, today.month, today.day, theHour, theMinute, today.second).timestamp(),
            })
            
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
            res = collectionVerifikasi.find({
                'email': data['email'],
                'expired_at': {'$gt': milisecond}
            }).sort('expired_at', pymongo.DESCENDING)
            if res != None:
                if int(res[0]['kode']) == int(data['kode']):
                    if data['detail'] == 'reset_password':
                        return {
                            'status': 'success',
                            'msg': 'Kode cocok!'
                        }
                    elif data['detail'] == 'activate_my_email':
                        make_verification_complete = collectionUser.update_one({
                            'email': res[0]['email']
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
    # except:
        return {
            'status': 'error',
            'msg': 'Kesalahan Server!'
        }

@app.route('/create-username', methods=['POST'])
def createUsername():
    data = request.json
    if data['username'] != '':
        res = collectionUser.update_one(
            {
                'email': data['email']
            },
            {
                '$set': {
                    'username': data['username']
                }
            }
        )

        return {
            'status': 'success',
            'msg': 'Username berhasil dibuat!'
        }
    else:
        return {
            'status': 'need_action',
            'msg': 'Silahkan isi username yang valid'
        }

@app.route('/check-username', methods=['POST'])
def checkUsername():
    data = request.json
    resUser = collectionUser.find_one({
        'email': data['email']
    })
    if resUser != None:
        resPasien = collectionPasien.find_one({
            'id_user': str(resUser['_id'])
        })
        if resPasien != None:
            if resPasien['username'] != '':
                return {
                    'status': 'success',
                    'msg': 'Username sudah kamu daftarkan!'
                }
            else:
                return {
                    'status': 'need_action',
                    'msg': 'Username belum kamu daftarkan!'
                }
        return {
            'status': 'error',
            'msg': 'Data lengkap kamu belum didaftarkan!'
        }
    return {
        'status': 'error',
        'msg': 'Email kamu tidak terdaftar pada database kami!'
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
            'username': '',
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

@app.route('/reset-password', methods=['POST'])
def resetPaswword():
    try:
        data = request.json
        res = collectionUser.find_one({
            'email': data['email']
        })

        if res != None:
            res = collectionUser.update_one({
                'email': data['email']
            },{
                '$set': {
                    'password': data['password']
                }
            })
            return {
                'status': 'success',
                'msg': 'Reset password berhasil'
            }
        
        return {
            'status': 'error',
            'msg': 'Reset password gagal'
        }
    except:
        return {
            'status': 'error',
            'msg': 'Reset password gagal'
        }

@app.route('/get/data-user/all/data', methods=['GET'])
def getAllDataUser():
    res = collectionUser.find({})
    hasil = []

    for data in res:
        data['_id'] = str(data['_id'])
        if data['username'] == '':
            data['username'] = '<i>Username belum terdaftar</i>'
        hasil.append(data)
    
    return {
        'status': 'success',
        'data_user': hasil

    }

@app.route('/add/data-user', methods=['POST'])
def addDataUser():
    data = request.json
    res = collectionUser.insert_one({
        'email': data['email'],
        'role': data['role'],
        'username': data['username'],
        'password': data['password'],
        'is_verified': False
    })

    return {
        'status': 'success'
    }

@app.route('/get/data-user', methods=['GET'])
def getDataUser():
    try:
        dataUser = collectionUser.find({})
        hasil = []

        for data in dataUser:
            data['_id'] = str(data['_id'])
            hasil.append(data)

        return {
            'status': 'success',
            'data_user': hasil
        }
    except:
        return {
            'status': 'error'
        }

@app.route('/show/data-user/<id_user>', methods=['GET'])
def showDataUser(id_user):
    res = collectionUser.find_one({
        '_id': ObjectId(id_user)
    })

    res['_id'] = str(res['_id'])

    return {
        'status': 'success',
        'data_user': res
    }

@app.route('/edit/data-user/<id_user>', methods=['GET'])
def editDataUser(id_user):
    res = collectionUser.find_one({
        '_id': ObjectId(id_user)
    })

    res['_id'] = str(res['_id'])

    return {
        'status': 'success',
        'data_user': res
    }

@app.route('/update/data-user/<id_user>', methods=['POST'])
def updateDataUser(id_user):
    data = request.json
    res = collectionUser.update_one(
        {
            '_id': ObjectId(id_user)
        },
        {
            '$set': {
                'email': data['email'],
                'role': data['role'],
                'username': data['username']
            }
        }
    )

    return {
        'status': 'success',
    }

@app.route('/delete/data-user/<id_user>', methods=['GET'])
def deleteDataUser(id_user):
    res = collectionUser.delete_one({
        '_id': ObjectId(id_user)
    })

    return {
        'status': 'success',
    }

@app.route('/get/data-pasien', methods=['GET'])
def ambilDataUser():
    try:
        dataPasien = collectionPasien.find({})
        hasil = []
        for data in dataPasien:
            data['_id'] = str(data['_id'])
            data['id_user'] = str(data['id_user'])
            if data['gender'] == 'l':
                data['gender'] = 'Laki - Laki'
            else:
                data['gender'] = 'Perempuan'
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

@app.route('/show/data-pasien/<id_pasien>', methods=['GET'])
def showDataPasien(id_pasien):
    res = collectionPasien.find_one({
        '_id': ObjectId(id_pasien)
    })
    resUser = collectionUser.find_one({
        '_id': res['id_user']
    })
    
    res['email'] = resUser['email']
    res['_id'] = str(res['_id'])
    res['id_user'] = str(res['id_user'])

    return {
        'status': 'success',
        'data_pasien': res
    }

@app.route('/edit/data-pasien/<id_pasien>', methods=['GET'])
def editDatapasien(id_pasien):
    res = collectionPasien.find_one({
        '_id': ObjectId(id_pasien)
    })

    res['_id'] = str(res['_id'])
    res['id_user'] = str(res['id_user'])

    return {
        'status': 'success',
        'data_pasien': res
    }

@app.route('/update/data-pasien/<id_pasien>', methods=['POST'])
def updateDataPasien(id_pasien):
    data = request.json
    res = collectionPasien.update_one(
        {
            '_id': ObjectId(id_pasien)
        },
        {
            '$set': {
                'nama_depan': data['nama_depan'],
                'nama_belakang': data['nama_belakang'],
                'tanggal_lahir': data['tanggal_lahir'],
                'umur': data['umur'],
                'gender': data['gender'],
                'alamat': data['alamat'],
            }
        }
    )

    return {
        'status': 'success',
    }

@app.route('/delete/data-pasien/<id_pasien>', methods=['GET'])
def deleteDataPasien(id_pasien):
    res = collectionPasien.delete_one({
        '_id': ObjectId(id_pasien)
    })

    return {
        'status': 'success',
    }

@app.route('/create/data-pasien/', methods=['GET'])
def createDataPasien():
    res = collectionUser.find({})
    hasil = []

    for data in res:
        data['_id'] = str(data['_id'])
        hasil.append(data)

    return {
        'status': 'success',
        'data_user': hasil
    }

@app.route('/add/data-pasien', methods=['POST'])
def simpanDataUser():
    try:
        requestData = request.json
        insertData = collectionPasien.insert_one({
            'nama_depan': requestData['nama_depan'],
            'nama_belakang': requestData['nama_belakang'],
            'tanggal_lahir': requestData['tanggal_lahir'],
            'umur': requestData['umur'],
            'gender': requestData['jenis_kelamin'],
            'alamat': requestData['alamat'],
            'role': 'user',
            'id_user': ObjectId(requestData['id_user']),
        })
        return {
            'status': 'success'
        }
    except:
        return {
            'status': 'error',
            'msg': 'Terjadi kesalahan!'
        }
    
@app.route('/get/data-histori', methods=['GET'])
def getDataHistori():
    res = collectionHistori.find({})
    hasil = []

    for data in res:
        data['_id'] = str(data['_id'])
        data['data_user'] = collectionUser.find_one({
            '_id': ObjectId(data['id_user'])
        })
        data['data_pasien'] = collectionPasien.find_one({
            'id_user': ObjectId(data['id_user'])
        })
        data['data_user']['_id'] = str(data['data_user']['_id'])
        data['data_pasien']['_id'] = str(data['data_pasien']['_id'])
        data['data_pasien']['id_user'] = str(data['data_pasien']['id_user'])
        hasil.append(data)

    return {
        'status': 'success',
        'data_histori': hasil
    }

@app.route('/show/data-histori/<id_histori>', methods=['GET'])
def showDataHistori(id_histori):
    res = collectionHistori.find_one({
        '_id': ObjectId(id_histori)
    })
    
    res['_id'] = str(res['_id'])
    res['data_user'] = collectionUser.find_one({
        '_id': ObjectId(res['id_user'])
    })
    res['data_pasien'] = collectionPasien.find_one({
        'id_user': ObjectId(res['id_user'])
    })
    res['data_user']['_id'] = str(res['data_user']['_id'])
    res['data_pasien']['_id'] = str(res['data_pasien']['_id'])
    res['data_pasien']['id_user'] = str(res['data_pasien']['id_user'])

    return {
        'status': 'success',
        'data_histori': res
    }

@app.route('/lakukan-prediksi', methods=['POST'])
def lakukanPrediksi():
    try:
        data = request.json
        load_model = joblib.load('model/SVM-Model.pkl')
        load_scaler = joblib.load('model/SVM-StandartScaler.pkl')

        data_norm = load_scaler.transform(
            np.array([[
                float(data['pregnancies']),
                float(data['glucose']),
                float(data['blood_pressure']),
                float(data['skin_thickness']),
                float(data['insulin']),
                float(data['bmi']),
                float(data['diabetes_pedigree_function']),
                float(data['age'])
            ]])
        )
        result = load_model.predict(data_norm)

        res = collectionHistori.insert_one({
            'pregnancies': float(data['pregnancies']),
            'glucose': float(data['glucose']),
            'blood_pressure': float(data['blood_pressure']),
            'skin_thickness': float(data['skin_thickness']),
            'insulin': float(data['insulin']),
            'bmi': float(data['bmi']),
            'diabetes_pedigree_function': float(data['diabetes_pedigree_function']),
            'age': float(data['age']),
            'outcome': int(result[0]),
            'id_user': data['id_user'],
            'created_at': datetime.now(timezone.utc),
        })

        return {
            'status': 'success',
            'result': int(result[0]),
            'data': data
        }
    except Exception as e:
        return {
            'status': 'error',
            'msg': 'Kesalahan pada server!',
            'stack': e
        }   

@app.route('/get/data-histori/user', methods=['POST'])
def getDataHistoriUser():
    data = request.json
    res = collectionHistori.find({
        'id_user': data['id_user']
    }).sort('created_at', pymongo.DESCENDING)
    hasil = []
    for data_histori in res:
        data_histori['_id'] = str(data_histori['_id'])
        data_histori['id_user'] = str(data_histori['id_user'])
        hasil.append(data_histori)

    return {
        'status': 'success',
        'data_histori': hasil
    }

@app.route('/get/data-glukosa/user', methods=['POST'])
def getDataGlukosaUser():
    data = request.json
    res = collectionHistori.find({
        'id_user': data['id_user']
    }).limit(7).sort('created_at', pymongo.DESCENDING)
    hasil = []

    for glukosa in res:
        glukosa['_id'] = str(glukosa['_id'])
        glukosa['id_user'] = str(glukosa['id_user'])
        hasil.append(glukosa)

    return {
        'status': 'success',
        'data_glukosa': hasil
    }

@app.route('/get/rata-glukosa/user', methods=['POST'])
def getRataRataGlukosaUser():
    data = request.json
    res = collectionHistori.find({
        'id_user': data['id_user']
    })
    hasil = 0
    i = 0

    for glukosa in res:
        hasil += float(glukosa['glucose'])
        i += 1

    return {
        'status': 'success',
        'rata_rata_glukosa': hasil / i
    }