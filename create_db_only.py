from models import *
# from db import session, init_db
import codecs
import sys
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
import json
import requests
import os
from flask import Flask, render_template, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Table, Column, ForeignKey, Integer, String, Boolean, Float # Added a bit here to create association tables...
from sqlalchemy.orm import relationship

db=SQLAlchemy(app)
session=db.session

app=Flask(__name__)
app.debug = True
app.use_reloader = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///./restaurants2.sqlite'
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

ZOMATO_KEY='8c60759775c7b9e0560fb1c82f8034b7'

CACHE_FNAME = "finalproject_cached_data.json"

#set up caching - first try opening CACHE_FNAME file for reading
try:
    file_obj=open(CACHE_FNAME,"r")
    file_contents=file_obj.read()
    CACHE_DICTION=json.loads(file_contents)
    file_obj.close()

#if it doesn't exist, make a new dictionary to put into cache file
except:
    CACHE_DICTION={}

#keep the API key secret
def params_unique_combination(baseurl, params_diction, private_keys=["apikey"]):
    alphabetized_keys = sorted(params_diction.keys())
    res = []
    for k in alphabetized_keys:
        if k not in private_keys:
            res.append("{}-{}".format(k, params_diction[k]))
    return baseurl + "_".join(res)

#function to request data and cache
def get_zomato_data(lat, lon, entity, entity_id, start, sort='rating', count=20):
    baseurl="https://developers.zomato.com/api/v2.1/search"
    params_diction={}
    params_diction['apikey']=ZOMATO_KEY
    params_diction['lat']=lat
    params_diction['lon']=lon
    params_diction['entity type']=entity
    params_diction['entity_id']=entity_id
    params_diction['start']=start
    params_diction['count']=count
    params_diction['sort']=sort
    unique_identifier=params_unique_combination(baseurl,params_diction)
    if unique_identifier in CACHE_DICTION:
        # print('retrieving data from cache')
        return CACHE_DICTION[unique_identifier]
    else:
        # print('making new request')
        resp=requests.get(baseurl,params=params_diction)
        python_object=json.loads(resp.text)
        with open(CACHE_FNAME, 'w') as f:
            CACHE_DICTION[unique_identifier] = python_object
            f.write(json.dumps(CACHE_DICTION))
        return python_object

#get the top 100 restaurants sorted by rating
get_zomato_data("42.27242033", "-83.7376774235", "subzone", 118000, 0)
get_zomato_data("42.27242033", "-83.7376774235", "subzone", 118000, 20)
get_zomato_data("42.27242033", "-83.7376774235", "subzone", 118000, 40)
get_zomato_data("42.27242033", "-83.7376774235", "subzone", 118000, 60)
get_zomato_data("42.27242033", "-83.7376774235", "subzone", 118000, 80)

#extract the data from json file
file=open('finalproject_cached_data.json', 'r', encoding='utf-8')
zomato_dictionaries=json.loads(file.read())
file.close()
data_restaurants=[]
data_cuisines=[]
unique_restaurants=[]
unique_cuisines=[]
urls=[]

#index into the json data and get all the info we need
for i in ["0", "20", "40", "60", "80"]:
    urls+=["https://developers.zomato.com/api/v2.1/searchcount-20_entity type-subzone_entity_id-118000_lat-42.27242033_lon--83.7376774235_sort-rating_start-"+i]
for url in urls: #for each request
    for d in zomato_dictionaries[url]["restaurants"]: #for each list
        data_restaurants.append(tuple((d['restaurant']['name'], d['restaurant']['location']['latitude'], d['restaurant']['location']['longitude'], d['restaurant']['user_rating']['aggregate_rating'], d['restaurant']['cuisines'].split(",")[0])))
        for item in data_restaurants:
            if item not in unique_restaurants:
                unique_restaurants.append(item)
        for k in list(d['restaurant'].keys()):
            if k=="cuisines": #if k is cuisines
                if d['restaurant'][k]!="":
                    data_cuisines+=[d['restaurant'][k].split()[0].strip(",")]
for item in data_cuisines:
    if item not in unique_cuisines:
        unique_cuisines.append(item)

#set up the database
# init_db()

class Cuisine(db.Model):
    __tablename__ = 'cuisine'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(250), nullable=False)
    def __repr__(self):
        return "{}".format(self.name)
    # When we pull this into another system, we'll do two steps in one. For now, this works.

class Restaurant(db.Model):
    __tablename__ = 'restaurant' # special variable useful for referencing in other/later code
    id = Column(Integer, primary_key=True, autoincrement=True) # autoincrements by default
    name = Column(String(250), nullable=False) # The way we write types in SQLAlchemy is different from SQLite specifically -- and more like Python!
    lat = Column(Float)
    lon = Column(Float)
    rating = Column(Float)
    cuisine = relationship("Cuisine", backref="Restaurant")
    cuisine_id=Column(Integer, ForeignKey('cuisine.id'))
    def __repr__(self):
        return "{} has {} cuisine and is rated {} out of 5".format(self.name, self.cuisine, self.rating)


for item in unique_cuisines:
    new_cuisine=Cuisine(name=item)
    session.add(new_cuisine)
    session.commit()
for item in unique_restaurants:
    new_restaurant=Restaurant(name=item[0], lat=item[1], lon=item[2], rating=item[3], cuisine_id=session.query(Cuisine.id).filter(Cuisine.name.like(item[4])))
    session.add(new_restaurant)
    session.commit()



@app.route('/')
def welcome():
    restaurant_list=[]
    get_restaurants=Restaurant.query.all()
    for r in get_restaurants:
        restaurant_list.append((r.name))
    return '<h1>Welcome to the restaurant app! There are {} top-rated restaurants in the database.</h1>'.format(len(restaurant_list))

# make query to database and show information on the page
if __name__=='__main__':
    db.create_all()
    app.run()
