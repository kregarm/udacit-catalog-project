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
   
@app.route('/category/<int:category_id>/edit/', methods=['GET', 'POST'])
def editCategory(category_id):
    category = session.query(Categories).filter_by(id = category_id).one()
    print category
    if request.method == 'GET':
        return render_template('edit-category.html', category = category)
    if request.method == 'POST':
        category.name = request.form['name']
        session.add(category)
        session.commit()
        return redirect(url_for('showItems', category_id = category_id))

@app.route('/category/<int:category_id>/delete/', methods=['GET'])
def deleteCategory(category_id):
    category = session.query(Categories).filter_by(id = category_id).one()
    categories = session.query(Categories).order_by(asc(Categories.name))
    if request.method == "GET":
        session.delete(category)
        session.commit()
        return redirect(url_for('showLanding'))

@app.route('/<int:category_id>/items/')
def showItems(category_id):
    categories = session.query(Categories).order_by(asc(Categories.name))
    category = session.query(Categories).filter_by(id = category_id).one()
    items = session.query(Item).filter_by(categories_id = category_id)
    return render_template('show-items.html', categories = categories, items = items, category = category)
    
@app.route('/<int:category_id>/<int:item_id>/')
def showItem(category_id, item_id):
    categories = session.query(Categories).order_by(asc(Categories.name))
    category = session.query(Categories).filter_by(id = category_id).one()
    item = session.query(Item).filter_by(id = item_id).one()
    return render_template('show-item.html', item = item, category = category, categories = categories)

@app.route('/<int:category_id>/items/new/', methods=['GET', 'POST'])
def newItem(category_id):
    categories = session.query(Categories).order_by(asc(Categories.name))
    if request.method == 'POST':
        newItem = Item(name = request.form['name'], description = request.form['description'], categories_id = request.form['category_id'])
        session.add(newItem)
        session.commit()
        return redirect(url_for('showItems',category_id = category_id))
    if request.method == 'GET':
        return render_template('new-item.html', categories = categories)

@app.route('/<int:category_id>/items/<int:item_id>/edit/', methods=['GET', 'POST'])
def editItem(category_id, item_id):
    category = session.query(Categories).filter_by(id = category_id).one()
    categories = session.query(Categories).order_by(asc(Categories.name))
    item = session.query(Item).filter_by(id = item_id).one()
    if request.method == 'GET':
        return render_template('edit-item.html', item = item, category = category, categories = categories)
    if request.method == 'POST':
        if request.form['name']:
            item.name = request.form['name']
        if request.form['description']:
            item.description = request.form['description']
        if request.form['category_id']:
            item.categories_id = request.form['category_id']
            #Reassigned category_id to properly redirect a user if there was a category change
            category_id = request.form['category_id']
        session.add(item)
        session.commit()
        return redirect(url_for('showItem', category_id = category_id, item_id = item_id))
        
@app.route('/<int:category_id>/<int:item_id>/delete/', methods=['GET'])
def deleteItem(category_id, item_id):
    category = session.query(Categories).filter_by(id = category_id).one()
    categories = session.query(Categories).order_by(asc(Categories.name))
    item = session.query(Item).filter_by(id = item_id).one()
    if request.method == "GET":
        session.delete(item)
        session.commit()
        return redirect(url_for('showItems', category_id = category_id))

@app.route('/categories/json/')
def showJsonCategories():
    categories = session.query(Categories).all()
    return jsonify(categories = [c.serialize for c in categories])

@app.route('/items/json/')
def showJsonItems():
    items = session.query(Item).all()
    return jsonify(items = [i.serialize for i in items])


if __name__ == '__main__':
    #app.secret_key = 'super_secret_key'
    app.debug = True
    app.run (host = '0.0.0.0', port = 5000)