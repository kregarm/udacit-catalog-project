from flask import Flask
from flask import render_template
from flask import request
from flask import redirect
from flask import jsonify
from flask import url_for
from flask import flash
from sqlalchemy import create_engine
from sqlalchemy import asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base
from database_setup import Categories
from database_setup import Item
from database_setup import User
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Catalog app"

engine = create_engine('sqlite:///catalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)


@app.route('/gconnect', methods=['POST'])
def gconnect():

    '''
    This function gathers data from Google API and stores it into a session
    variable. If it is a new user this function creates a new entry into
    the database and also populates the redirect view with the user's data.
    '''

    # Validate token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('invalid state paramater'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Get auth code
    code = request.data

    try:
        # Upgrade the auth code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except:
        response = make_response(
            json.dumps('Could not upgrade the auth code'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check if the token is valid
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    response = h.request(url, 'GET')[1]
    result = json.loads(response.decode('utf-8'))

    # Abort if there was an error in the access token
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the token is used for the correct user
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify the token is valid for this app
    if result['issued_to'] != CLIENT_ID:
        response.make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print ("Token's client ID does not match app's.")
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps
                                 ('Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # store the access token to session
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info from google
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    # Store info from Google to login_session
    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    user_id = getUserId(login_session['email'])

    # Create a new user if it does not yet exists
    if user_id is None:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    # Login and redirect view which populates the modal
    # on the landing.html template
    print('this is the login session')
    print(login_session)
    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ''' " style = "width: 300px; height: 300px;
    border-radius: 150px;-webkit-border-radius: 150px;
    -moz-border-radius: 150px;"> '''
    flash("you are now logged in as %s" % login_session['username'])
    print ("done!")
    return output


def createUser(login_session):
    session = DBSession()
    newUser = User(name=login_session['username'],
                   email=login_session['email'],
                   picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    session = DBSession()
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserId(user_email):
    session = DBSession()
    try:
        user = session.query(User).filter_by(email=user_email).one()
        return user.id
    except:
        return None


@app.route('/gdisconnect')
def gdisconnect():

    '''
    This function logs out a user, clears his login_session
    and redirects him back to the landing page.
    '''

    access_token = login_session.get('access_token')
    if access_token is None:
        print ('Access Token is None')
        response = make_response(json.dumps
                                 ('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    print ('In gdisconnect access token is %s', access_token)
    print ('User name is: ')
    print (login_session['username'])
    at = login_session['access_token']
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % at
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        del login_session['access_token']
        del login_session['state']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return redirect(url_for('showLanding'))
    else:
        response = make_response(json.dumps
                                 ('Failed to revoke token for given user.',
                                  400))
        response.headers['Content-Type'] = 'application/json'
        return response


@app.route('/')
def showLanding():

    '''
    Creates the state used for authentication, queries the database
    and renders the landing page template.
    '''

    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in range(32))
    login_session['state'] = state
    session = DBSession()
    categories = session.query(Categories).order_by(asc(Categories.name))
    return render_template('landing.html', categories=categories, STATE=state)


@app.route('/category/new/', methods=['GET', 'POST'])
def newCategory():

    '''
    Checks if a user is logged in, provides the html template on
    GET request and stores data into the DB on POST request. It
    also takes care of the flash message.
    '''

    if 'username' not in login_session:
        return redirect(url_for('showLanding'))
    session = DBSession()
    if request.method == 'POST':
        newCategory = Categories(name=request.form['name'],
                                 user_id=login_session['user_id'])
        session.add(newCategory)
        flash('New category %s created' % newCategory.name)
        session.commit()
        return redirect(url_for('showLanding'))
    else:
        return render_template('new-category.html')


@app.route('/category/<int:category_id>/edit/', methods=['GET', 'POST'])
def editCategory(category_id):

    '''
    Connects to the DB, queries the categories and checks if a user is
    logged in. It also checks if is the same user who created the
    category and redirects the users if they aren't the creators of
    the category.
    It provides the html template on GET request and stores data
    into the DB on POST request.
    Authorization check is also made on the POST method.
    Function takes care of the flash message.

    :param category_id: the ID of the edited category
    '''

    session = DBSession()
    category = session.query(Categories).filter_by(id=category_id).one()
    if ('username' not in login_session or
       category.user_id != login_session['user_id']):
        return redirect(url_for('showLanding'))
    if request.method == 'GET':
        return render_template('edit-category.html', category=category)
    if request.method == 'POST':
        if login_session['user_id'] != category.user_id:
            return "Unauthorized request"

        category.name = request.form['name']
        session.add(category)
        flash('Category %s edited' % category.name)
        session.commit()
        return redirect(url_for('showItems', category_id=category_id))


@app.route('/category/<int:category_id>/delete/', methods=['POST'])
def deleteCategory(category_id):

    '''
    Connects to the DB and queries the categories. It only allows POST
    request and makes another check that the user who is trying to
    delete the category is also the one who made it.
    Function takes care of the flash message.

    :param category_id: the ID of the selected category
    '''

    session = DBSession()
    category = session.query(Categories).filter_by(id=category_id).one()
    categories = session.query(Categories).order_by(asc(Categories.name))
    if request.method == "POST":
        if login_session['user_id'] != category.user_id:
            return "Unauthorized request"
        session.delete(category)
        session.commit()
        flash('Category %s deleted' % category.name)
        return redirect(url_for('showLanding'))


@app.route('/<int:category_id>/items/')
def showItems(category_id):

    '''
    Connects to the DB and queries the items for the selected category
    and renders the template.

    :param category_id: the ID of the selected category
    '''

    session = DBSession()
    categories = session.query(Categories).order_by(asc(Categories.name))
    category = session.query(Categories).filter_by(id=category_id).one()
    items = session.query(Item).filter_by(categories_id=category_id)
    return render_template('show-items.html', categories=categories,
                           items=items, category=category,
                           user_id=login_session['user_id'])


@app.route('/<int:category_id>/<int:item_id>/')
def showItem(category_id, item_id):

    '''
    Connects to the DB and queries the item from the selected category
    and renders the template.

    :param category_id: the ID of the selected category
    :param item_id: the ID of the selected item
    '''

    session = DBSession()
    categories = session.query(Categories).order_by(asc(Categories.name))
    category = session.query(Categories).filter_by(id=category_id).one()
    item = session.query(Item).filter_by(id=item_id).one()
    return render_template('show-item.html', item=item,
                           category=category, categories=categories,
                           user_id=login_session['user_id'])


@app.route('/<int:category_id>/items/new/', methods=['GET', 'POST'])
def newItem(category_id):

    '''
    Checks if a user is logged in, provides the html template on
    GET request and stores data into the DB on POST request. It
    also takes care of the flash message.
    '''

    session = DBSession()
    categories = session.query(Categories).order_by(asc(Categories.name))
    if request.method == 'POST':
        newItem = Item(name=request.form['name'],
                       description=request.form['description'],
                       categories_id=request.form['category_id'],
                       user_id=login_session['user_id'])
        session.add(newItem)
        flash('Item %s added' % newItem.name)
        session.commit()
        return redirect(url_for('showItems', category_id=category_id))
    if request.method == 'GET':
        if 'username' not in login_session:
            return redirect(url_for('showLanding'))
        else:
            return render_template('new-item.html', categories=categories)


@app.route('/<int:category_id>/items/<int:item_id>/edit/',
           methods=['GET', 'POST'])
def editItem(category_id, item_id):

    '''
    Connects to the DB, queries the categories, items and checks if a user is
    logged in and it is the same user who created the item. Function redirects
    the users if they aren't the creators of the item. It provides the html
    template on GET request and stores data into the DB on POST request.
    Authorization check is also made on the POST request.
    Function takes care of the flash message.

    :param category_id: the ID of the selected category
    :param item_id: the ID of the edited item
    '''

    session = DBSession()
    category = session.query(Categories).filter_by(id=category_id).one()
    categories = session.query(Categories).order_by(asc(Categories.name))
    item = session.query(Item).filter_by(id=item_id).one()
    if request.method == 'GET':
        if ('username' not in login_session or
           item.user_id != login_session['user_id']):
            return redirect(url_for('showLanding'))
        else:
            return render_template('edit-item.html', item=item,
                                   category=category, categories=categories)
    if request.method == 'POST':
        if login_session['user_id'] != item.user_id:
            return "Unauthorized request"
        item.name = request.form['name']
        item.description = request.form['description']
        item.categories_id = request.form['category_id']

        # Reassigned category_id to properly redirect a user
        # if there was a category change
        category_id = request.form['category_id']

        session.add(item)
        flash('Item %s edited' % item.name)
        session.commit()
        return redirect(url_for('showItem', category_id=category_id,
                        item_id=item_id))


@app.route('/<int:category_id>/<int:item_id>/delete/', methods=['POST'])
def deleteItem(category_id, item_id):

    '''
    Connects to the DB and queries the categories and items.
    It only allows POST request and makes another check that the user
    who is trying to delete the item is also the one who made it.
    Function takes care of the flash message.

    :param category_id: the ID of the selected category
    :param item_id: the ID of the item a user wishes to delete
    '''

    session = DBSession()
    category = session.query(Categories).filter_by(id=category_id).one()
    categories = session.query(Categories).order_by(asc(Categories.name))
    item = session.query(Item).filter_by(id=item_id).one()
    if request.method == "POST":
        if login_session['user_id'] != item.user_id:
            return "Unauthorized request"
        session.delete(item)
        session.commit()
        flash('Item %s deleted' % item.name)
        return redirect(url_for('showItems', category_id=category_id))


@app.route('/categories/json/')
def showJsonCategories():
    session = DBSession()
    categories = session.query(Categories).all()
    return jsonify(categories=[c.serialize for c in categories])


@app.route('/items/json/')
def showAllJsonItems():
    session = DBSession()
    items = session.query(Item).all()
    return jsonify(items=[i.serialize for i in items])


@app.route('/<int:category_id>/items/json/')
def showJsonItemsFromOneCategory(category_id):
    session = DBSession()
    items = session.query(Item).filter_by(categories_id=category_id).all()
    return jsonify(items=[i.serialize for i in items])


@app.route('/items/<int:item_id>/json/')
def showJsonItem(item_id):
    session = DBSession()
    items = session.query(Item).filter_by(id=item_id).all()
    return jsonify(items=[i.serialize for i in items])


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
