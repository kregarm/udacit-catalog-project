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
@app.route('/category/<int:category_id>/edit/', methods=['GET', 'POST'])
def editCategory():

@app.route('category/<int:category_id>/delete/', methods=['GET', 'POST'])
def deleteCategory():
'''

@app.route('/<int:category_id>/items/')
def showItems(category_id):
    categories = session.query(Categories).order_by(asc(Categories.name))
    category = session.query(Categories).filter_by(id = category_id).one()
    items = session.query(Item).filter_by(categories_id = category_id)
    return render_template('show-items.html', categories = categories, items = items, category = category)
    
'''
@app.route('/<int:category_id>/<int:item_id>/')
def showItem():
'''

@app.route('/<int:category_id>/items/new/', methods=['GET', 'POST'])
def newItem(category_id):
    if request.method == 'POST':
        newItem = Item(name = request.form['name'], description = request.form['description'], categories_id = category_id)
        session.add(newItem)
        session.commit()
        return redirect(url_for('showItems',category_id = category_id))
    if request.method == 'GET':
        return render_template('new-item.html')
'''
@app.route('<int:category_id>/<int:item_id>/edit/', methods=['GET', 'POST'])
def editItem():

@app.route('/<int:category_id>/<int:item_id>/delete/', methods=['GET', 'POST']))
def deleteItem()
'''

if __name__ == '__main__':
    #app.secret_key = 'super_secret_key'
    app.debug = True
    app.run (host = '0.0.0.0', port = 5000)