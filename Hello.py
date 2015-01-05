import os
from flask import Flask, url_for, render_template, redirect, request, g, jsonify, abort, make_response, flash
from flask.ext.sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Column, Integer, Text
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
# from flask.ext.httpauth import HTTPBasicAuth
from flask.ext.login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from passlib.apps import custom_app_context as pwd_context
import simplejson
import requests
import urllib



app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
db = SQLAlchemy(app)
# auth = HTTPBasicAuth()
lm = LoginManager(app)
lm.login_view = 'index'


LINK_PREFIX = "http://api.rottentomatoes.com/api/public/v1.0/movies.json?q="
LINK_SUFFIX = "&page_limit=15&page=1&apikey="

##################### MODELS & Dependancies #############################
usermovie = db.Table('usermovie', db.Column('user_id', db.Integer, db.ForeignKey('users.id')), db.Column('movie_id', db.Integer, db.ForeignKey('movies.id')))

class User(UserMixin, db.Model):
	__tablename__ = 'users'
	id = db.Column(db.Integer, primary_key=True)
	username = Column(db.String(64), index=True, unique=True)
	password_hash = Column(db.String(128))
	movies = db.relationship('Movie', backref='user', lazy='dynamic', cascade='all, delete-orphan')
	def hash_password(self, password):
		self.password_hash = generate_password_hash(password)
	def verify_password(self, password):
		return check_password_hash(self.password_hash, password)

class Movie(db.Model):
	__tablename__ = 'movies'
	id = db.Column(db.Integer, primary_key=True)
	title = Column(db.String(64), index=True, unique=False)
	thumbnail = Column(Text, unique=False)
	year = Column(db.Integer)
	criticsrate = Column(db.Integer)
	review = Column(Text, unique=False)
	rate = Column(db.Integer)
	watched = Column(db.Boolean, default = False)
	user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
	#reviews = db.relationship('Review', uselist=False, backref='movie', lazy='dynamic', cascade='all, delete-orphan')
	#rates = db.relationship('Rate', uselist=False, backref='movie', lazy='dynamic', cascade='all, delete-orphan')


# class Review(db.Model):
# 	__tablename__ = 'reviews'
# 	id = db.Column(db.Integer, primary_key=True)
# 	comment = Column(db.String, unique=False)
# 	movie_id = db.Column(db.Integer, db.ForeignKey('movies.id'), index=True)

# class Rate(db.Model):
# 	__tablename__ = 'rates'
# 	id = db.Column(db.Integer, primary_key=True)
# 	rate = Column(db.Integer, unique=True)
# 	movie_id = db.Column(db.Integer, db.ForeignKey('movies.id'), index=True)

###################### UTULITIES ###############################

# @auth.verify_password
# def verify_password(username, password):
# 	user = User.query.filter_by(username = username).first()
# 	if not user or not user.verify_password(password):
# 		return False
# 	g.user = user
# 	return True

#def tojson(): array of json for movies, coments and rates

@lm.user_loader
def load_user(id):
	return User.query.get(int(id))


#from .errors import forbidden_error
#@api.before_request
#@auth.login_required 
#def before_request():
#    if not g.current_user.is_anonymous and not g.current_user.confirmed:
#        return forbidden('Unconfirmed account')

####################### API CALL ###############################

#def getMovies(title):
#
#    if " " in title:
#        parts = title.split(" ")
#        title = "+".join(parts)
# 
#
#    url = "{d}{d}{d}{d}".format(LINK_PREFIX, title, LINK_SUFFIX, API_KEY)
#    res = requests.get(url)
#    js = simplejson.loads(res.content)
#    l = []
#    for movie in js["movies"].["title"]:
#        l.append(movie)
#    return l

####################### ROUTES #################################

@app.route('/', methods=['GET', 'POST'])
def index():
	error = None
	if request.method == 'POST':
		try:
			user = User.query.filter_by(username=request.form['username']).first()
			if user is None or not user.verify_password(request.form['password']):
				return redirect(url_for('index', **request.args))
			else:
				login_user(user)
				return redirect(request.args.get('next') or url_for('home'))
		except ValueError:
			print("Oops!  That was no valid number.  Try again...")
	return render_template('index.html', error=error)

@app.route('/register', methods = ['POST'])
def new_user():
	username = request.form['username']
	password = request.form['password']
	if username is '' or password is '':
		#abort(400)
		return redirect(url_for('index')) 
	if User.query.filter_by(username = username).first() is not None:
		return redirect(url_for('index'))
	user = User(username = username)
	user.hash_password(password)
	db.session.add(user)
	db.session.commit()
	flash('Registered successfully, try login')
	return redirect(url_for('index'))
	#return users jsonified data

@app.route('/search/<string:skey>' , methods = ['GET'])
@login_required
def search(skey):
	title = skey
	if " " in title:
		parts = title.split(" ")
		title = "+".join(parts)
 
	url = "{0}{1}{2}{3}".format(LINK_PREFIX, title, LINK_SUFFIX, API_KEY)
	res = requests.get(url)
	js = simplejson.loads(res.content)
	l = []
	for movie in js['movies']:
		temp_movie = {}
		temp_movie["title"] = movie['title']
		temp_movie["year"] = movie['year']
		temp_movie["critic"] = movie['ratings']['critics_score']
		temp_movie["thumbnail"] = movie['posters']['thumbnail']
		l.append(dict(temp_movie))
	return jsonify({'movies': l})

@app.route('/home', methods = ['GET', 'POST'])
@login_required
def home():
	return render_template('home.html')


@app.route('/fetch', methods = ['GET'])
@login_required
def fetch():

	movieqry = Movie.query.filter(Movie.user_id == current_user.id).all()
	templis = []
	tempdic = {}
	for i in movieqry:
	    tempdic = {
	        'id' : i.id,
	        'title' : i.title,
	        'year' : i.year,
	        'critic' : i.criticsrate,
	        'review' : i.review,
	        'rate' : i.rate,
	        'thmbnl' : i.thumbnail,
	        'watched': i.watched
	    }
	    templis.append(tempdic)
	return jsonify({'movies': templis}) 

@app.route('/add', methods = ['POST'])
@login_required
def addMovie():
	if not request.json or not 'title' in request.json:
		abort(400)
	#tempMovie = Movie()
	tempMovie = Movie(
		# 'id': movies[-1]['id'] + 1,
		title = request.json['title'],
		year = request.json['year'],
		watched = False,
		thumbnail = request.json['thmbnl'],
		criticsrate = request.json['critic'],
		user = current_user
	)
	try:
		db.session.add(tempMovie)
		db.session.commit()
	except:
		return make_response(jsonify({'error': 'Failed to add movie.'}), 404)
	tmpmv = Movie.query.filter_by(title=tempMovie.title).first()
	rtnid = tmpmv.id
	return jsonify({'status': 'Movie added successfully.', 'id': rtnid}), 201


@app.route('/deletemovie', methods = ['POST'])
@login_required
def deletemovie():
	if not request.json or not 'mvid' in request.json:
		abort(400)

	mvid = request.json['mvid']
	try:
		tempMovie = Movie.query.filter_by(id=mvid).first()
		db.session.delete(tempMovie)
		db.session.commit()
	except:
		return make_response(jsonify({'error': 'Failed to delete movie.'}), 404)
	
	return jsonify({'status': 'Movie deleted successfully.'}), 201
	
@app.route('/addcomment', methods = ['POST'])
@login_required
def addComment():
	if not request.json or not 'comment' or not 'title' in request.json:
		abort(400)

	cmnt = request.json['comment']
	mvttl = request.json['title']
	try:
		selectedmovie = Movie.query.filter_by(title=mvttl).first()
		selectedmovie.review = cmnt
		db.session.commit()
	except:
		return make_response(jsonify({'error': 'Failed to add comment.'}), 404)
	
	return jsonify({'status': 'comment added successfully.'}), 201


@app.route('/checked', methods = ['POST'])
@login_required
def checked():
	if not request.json or not 'checked' or not 'mvid' in request.json:
		abort(400)
	mvid = request.json['mvid']
	chkd = request.json['checked']
	try:
		selectedmovie = Movie.query.filter_by(id=mvid).first()
		selectedmovie.watched = chkd
		db.session.commit()
	except:
		return make_response(jsonify({'error': 'Failed to change.'}), 404)
	
	return jsonify({'status': 'Changed to watched successfully.'}), 201


@app.route('/rate', methods = ['POST'])
@login_required
def changeRate():
	if not request.json or not 'rate' or not 'mvid' in request.json:
		abort(400)
	mvid = request.json['mvid']
	chkd = request.json['rate']
	try:
		selectedmovie = Movie.query.filter_by(id=mvid).first()
		selectedmovie.rate = chkd
		db.session.commit()
	except:
		return make_response(jsonify({'error': 'Failed to save your rate.'}), 404)
	
	return jsonify({'status': 'Your rate added successfully.'}), 201

@app.route('/logout')
@login_required
def logout():
  logout_user()
  return redirect(url_for('index'))

####################### RUN ####################################
db.create_all()
app.debug = False

if __name__ == '__main__':
	app.run()
