from flask import Flask, render_template, request, redirect,jsonify, url_for, flash
app = Flask(__name__)

from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Categories, Item, User

from flask import session as login_session
import random, string

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError

import httplib2
import json
from flask import make_response
import requests

engine = create_engine('sqlite:///catalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

#@app.route('/login')
#def showLogin():

@app.route('/')
def showLanding():
    categories = session.query(Categories).order_by(asc(Categories.name))
    return render_template('landing.html', categories = categories)
    

@app.route('/category/new/', methods=['GET', 'POST'])
def newCategory():
    if request.method == 'POST':
        newCategory = Categories(name = request.form['name'])
        session.add(newCategory)
        session.commit()
        return redirect(url_for('showLanding'))
    else: 
        return render_template('new-category.html')
'''    
@app.route('/category/<str:category_name>/edit/', methods=['GET', 'POST'])
def editCategory():

@app.route('category/<str:category_name>/delete/', methods=['GET', 'POST'])
def deleteCategory():
'''

@app.route('/<int:category_id>/items/')
def showItems(category_id):
    categories = session.query(Categories).order_by(asc(Categories.name))
    return render_template('show-items.html', categories = categories)
    
'''
@app.route('/<str:category_name>/<str:item_name>/')
def showItem():

@app.route('/<str:category_name>/<str:item_name>/new/', methods=['GET', 'POST'])
def newItem():

@app.route('/<str:category_name>/<str:item_name>/edit/', methods=['GET', 'POST'])
def editItem():

@app.route('/<str:category_name>/<str:item_name>/delete/', methods=['GET', 'POST']))
def deleteItem()
'''

if __name__ == '__main__':
    #app.secret_key = 'super_secret_key'
    app.debug = True
    app.run (host = '0.0.0.0', port = 5000)