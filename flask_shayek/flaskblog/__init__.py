from flask import Flask, session, render_template, redirect, request
import pyrebase

app = Flask(__name__)
config = {
    "apiKey": "AIzaSyAXgzwyWNcfI-QSO_IbBVx9luHc9zOUzeY",
    "authDomain": "shayek-560ec.firebaseapp.com",
    "databaseURL": "https://shayek-560ec-default-rtdb.firebaseio.com",
    "projectId": "shayek-560ec",
    "storageBucket": "shayek-560ec.appspot.com",
    "messagingSenderId": "377837381829",
    "appId": "1:377837381829:web:d6594a9e9f6af83c1468ac",
    "measurementId": "G-PKCVFN45WE"
  }


firebase = pyrebase.initialize_app(config)
auth= firebase.auth()
app.config['SECRET_KEY'] = '44a724aea84a985aa8cec3f8c316cf2e'
from flaskblog import routes