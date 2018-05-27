from flask import Flask, render_template, request, redirect,jsonify, url_for, flash
app = Flask(__name__)

#This app secret is required by Flash message
app.secret_key = 'some_secret'

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

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Catalog app"

engine = create_engine('sqlite:///catalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)

@app.route('/gconnect', methods=['POST'])
def gconnect():
    #Validate token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('invalid state paramater'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    
    #Get auth code
    code = request.data

    try:
        #Upgrade the auth code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except:
        response = make_response(
            json.dumps('Could not upgrade the auth code'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    
    #Check if the token is valid
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    response = h.request(url, 'GET')[1]
    result = json.loads(response.decode('utf-8'))

    #Abort if there was an error in the access token
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    #Verify that the token is used for the correct user
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    
    #Verify the token is valid for this app
    if result['issued_to'] != CLIENT_ID:
        response.make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print ("Token's client ID does not match app's.")
        response.headers['Content-Type'] = 'application/json'
        return response
    
    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    
    login_session['access_token'] = credentials.access_token
    login_session['gplis_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    user_id = getUserId(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    print('this is the login session')
    print(login_session)
    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print ("done!")
    return output

def createUser(login_session):
    session = DBSession()
    newUser = User(name=login_session['username'], email = login_session['email'], picture = login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id

def getUserInfo(user_id):
    session = DBSession()
    user = session.query(User).filter_by(id=user_id).one()
    return user

def getUserId(email):
    session = DBSession()
    try:
        user = session.query(User).filter_by(email=user_email).one()
        return user.id
    except:
        return None



@app.route('/')
def showLanding():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(32))
    login_session['state'] = state
    session = DBSession()
    categories = session.query(Categories).order_by(asc(Categories.name))
    return render_template('landing.html', categories = categories, STATE = state)
    
@app.route('/category/new/', methods=['GET', 'POST'])
def newCategory():
    session = DBSession()
    if request.method == 'POST':
        newCategory = Categories(name = request.form['name'])
        session.add(newCategory)
        flash('New category %s created' % newCategory.name)
        session.commit()
        return redirect(url_for('showLanding'))
    else: 
        return render_template('new-category.html')
   
@app.route('/category/<int:category_id>/edit/', methods=['GET', 'POST'])
def editCategory(category_id):
    session = DBSession()
    category = session.query(Categories).filter_by(id = category_id).one()
    print category
    if request.method == 'GET':
        return render_template('edit-category.html', category = category)
    if request.method == 'POST':
        category.name = request.form['name']
        session.add(category)
        flash('Category %s edited' % category.name)
        session.commit()
        return redirect(url_for('showItems', category_id = category_id))

@app.route('/category/<int:category_id>/delete/', methods=['GET'])
def deleteCategory(category_id):
    session = DBSession()
    category = session.query(Categories).filter_by(id = category_id).one()
    categories = session.query(Categories).order_by(asc(Categories.name))
    if request.method == "GET":
        session.delete(category)
        session.commit()
        flash('Category %s deleted' % category.name)
        return redirect(url_for('showLanding'))

@app.route('/<int:category_id>/items/')
def showItems(category_id):
    session = DBSession()
    categories = session.query(Categories).order_by(asc(Categories.name))
    category = session.query(Categories).filter_by(id = category_id).one()
    items = session.query(Item).filter_by(categories_id = category_id)
    return render_template('show-items.html', categories = categories, items = items, category = category)
    
@app.route('/<int:category_id>/<int:item_id>/')
def showItem(category_id, item_id):
    session = DBSession()
    categories = session.query(Categories).order_by(asc(Categories.name))
    category = session.query(Categories).filter_by(id = category_id).one()
    item = session.query(Item).filter_by(id = item_id).one()
    return render_template('show-item.html', item = item, category = category, categories = categories)

@app.route('/<int:category_id>/items/new/', methods=['GET', 'POST'])
def newItem(category_id):
    session = DBSession()
    categories = session.query(Categories).order_by(asc(Categories.name))
    if request.method == 'POST':
        newItem = Item(name = request.form['name'], description = request.form['description'], categories_id = request.form['category_id'])
        session.add(newItem)
        flash('Item %s added' % newItem.name)
        session.commit()
        return redirect(url_for('showItems',category_id = category_id))
    if request.method == 'GET':
        return render_template('new-item.html', categories = categories)

@app.route('/<int:category_id>/items/<int:item_id>/edit/', methods=['GET', 'POST'])
def editItem(category_id, item_id):
    session = DBSession()
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
        flash('Item %s edited' % item.name)
        session.commit()
        return redirect(url_for('showItem', category_id = category_id, item_id = item_id))
        
@app.route('/<int:category_id>/<int:item_id>/delete/', methods=['GET'])
def deleteItem(category_id, item_id):
    session = DBSession()
    category = session.query(Categories).filter_by(id = category_id).one()
    categories = session.query(Categories).order_by(asc(Categories.name))
    item = session.query(Item).filter_by(id = item_id).one()
    if request.method == "GET":
        session.delete(item)
        session.commit()
        flash('Item %s deleted' % item.name)
        return redirect(url_for('showItems', category_id = category_id))

@app.route('/categories/json/')
def showJsonCategories():
    session = DBSession()
    categories = session.query(Categories).all()
    return jsonify(categories = [c.serialize for c in categories])

@app.route('/items/json/')
def showJsonItems():
    session = DBSession()
    items = session.query(Item).all()
    return jsonify(items = [i.serialize for i in items])


if __name__ == '__main__':
    #app.secret_key = 'super_secret_key'
    app.debug = True
    app.run (host = '0.0.0.0', port = 5000)