# Catalog project

Catalog app implements basic CRUD operations and Authentication&Authorization for learning purposes.

## Prerequisites and environement setup

This application uses the followig tools which need to be setup beforehand:

* GIT
* Vagrant (and the appropriate vagrantfile)
* Virtualbox

Step-by-step guide on how to setup you environment is provided by [Udacity](https://www.udacity.com/wiki/ud088/vagrant).

## Running the application

Once you have the environemnt set up, clone this repo into you vagrant folder. Open this folder in terminal and run the virtual machine using:

`vagrant up`

`vagrant ssh`

Once you have your virtual machine running, you will firstly need to create a db with the following command:

`python database_setup.py`

This repo does not provide a seed file so you will need to populate the database yourself. To start the application simply run:

`python app.py`

and go to your browser to the URL: localhost:5000

## Manual

As stated above this is a very simple app. You can view categories and items stored in a DB without having to log in, but if you want to add or edit DB entries you will have to log in.