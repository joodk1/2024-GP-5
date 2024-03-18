from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
# got key from command prompt python secrets.token_hex(16)
app.config['SECRET_KEY'] = '44a724aea84a985aa8cec3f8c316cf2e'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shayek.db'
db = SQLAlchemy(app)

from flaskblog import routes