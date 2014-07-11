from flask import *
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager
from flask.ext.mail import *
from urlparse import *

from password import *		# Handles password hasing
from credentials import *	# Holds credentials

import random
import string
import json
import requests
import md5
import datetime

'''
	Initializing basic variables and junk
'''

app = Flask(__name__)
connectionString = "mysql://%s:%s@%s:3306/%s" % (USERNAME, PASSWORD, HOSTNAME, DATABASE)
app.config['SQLALCHEMY_DATABASE_URI'] = connectionString
db = SQLAlchemy(app)
app.secret_key = SECRET_KEY

app.config.update(
		MAIL_SERVER=EMAIL_SERVER,
		MAIL_PORT=587,
		MAIL_USE_TLS=True,
		MAIL_USERNAME=EMAIL_USERNAME,
		MAIL_PASSWORD=EMAIL_PASSWORD
	)

mail = Mail(app)

app.permanent_session_lifetime = datetime.timedelta(days=30)

'''
	Class declarations
'''

class Admin(db.Model):
	__tablename__ = "admins"
	
	id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(80), unique=True)
        password = db.Column(db.String(50))
	
	def __init__(self, username, password):
		self.username = username
		self.password = password

class UsersDev(db.Model):
        __tablename__ = "usersdev"

	id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(80), unique=True)
        email = db.Column(db.String(120), unique=True)
        password = db.Column(db.String(50))
	random_type = db.Column(db.Integer)
	reset_url = db.Column(db.String(10))
	reset_expiration = db.Column(db.String(25))

        def __init__(self, username, email, password, random_type=0):
                self.username = username
                self.email = email
                self.password = password
		self.random_type = random_type
		self.reset_url = ""
		self.reset_expiration = ""

        def __repr__(self):
                return '<User %r>' % self.username

class Playlist(db.Model):
	__tablename__ = "playlists"
	
	id = db.Column(db.Integer, primary_key=True)
	user_id = db.Column(db.Integer)
	title = db.Column(db.String(100))
	public = db.Column(db.Integer)
	numSongs = db.Column(db.Integer)
	hash_value = db.Column(db.String(50))

	def __init__(self, user_id, title, public, hash_value):
		self.user_id = user_id
		self.title = title
		self.public = public
		self.numSongs = 0
		self.hash_value = hash_value

	def __repr__(self):
		return '<User %r>' % self.id

class Songs(db.Model):
	__tablename__ = "songs" 

	id = db.Column(db.Integer, primary_key=True)
	playlist_id = db.Column(db.Integer)
	user_id = db.Column(db.Integer)
	url = db.Column(db.String(200))
	weight = db.Column(db.Integer)
	title = db.Column(db.String(50))
	play_count = db.Column(db.Integer)
	suppress = db.Column(db.Integer)
	song_type = db.Column(db.Integer)

	def __init__(self, playlist_id, user_id, url, weight, title, song_type):
		self.user_id = user_id
		self.playlist_id = playlist_id
		self.url = url
		self.weight = weight
		self.title = title
		self.play_count = 0
		self.suppress = 0
		self.song_type = song_type

	def __repr__(self):
		return '<User %r>' % self.id 

class Tags(db.Model):
	__tablename__ = "tags"
	
	id = db.Column(db.Integer, primary_key=True)
	playlist_id = db.Column(db.Integer)
        user_id = db.Column(db.Integer)
	song_id = db.Column(db.Integer)
	tag_name = db.Column(db.String(20))

	def __init__(self, user_id, tag_name, song_id=0, playlist_id=0):
		self.user_id = user_id
		self.tag_name = tag_name
		self.song_id = song_id
		self.playlist_id = playlist_id

db.create_all()
db.session.commit()

'''
	Generic function definitions
'''

def getPlaylistID(url):
	query = urlparse(url)
	if query.hostname in ('www.youtube.com'):
		if query.path == "/view_play_list":
			p = parse_qs(query.query)
			return p['p'][0]
		if query.path == "/watch":
			p = parse_qs(query.query)
			return p['list'][0]
		if query.path == "/playlist":
			p = parse_qs(query.query)
			return p['list'][0]
	else:
		return url

def getResetURL(size=6, chars=string.ascii_uppercase + string.digits):
	return ''.join(random.choice(chars) for _ in range(size))

def getNumSongs(playlist_id):
	songs = Songs.query.filter_by(id=playlist_id).first()
	numSongs = 0
	for song in songs:
		numSongs += 1
	return numSongs

def playlistRandomizer(userid,playlist_id):
	songs = Songs.query.filter_by(playlist_id=playlist_id).all()
	if len(songs) == 1:
                for song in songs:
                        song.play_count += 1
                        db.session.commit()
                        return song
	largestValue = 0
	currentWinner = 0
	runnerUp = 0
	for song in songs:
		randomNumber = random.randint(1,100)
		holder = int(song.weight) * randomNumber
		if holder > largestValue:
			largestValue = holder
			currentWinner = song.id
		elif holder <= largestValue and holder > runnerUp:
			runnerUp = song.id	
	winner = Songs.query.filter_by(id=currentWinner).first()
	try:
		if winner.suppress == 1:
			winner.suppress = 0
                        db.session.commit()
                        winner = Songs.query.filter_by(id=runnerUp).first()
		elif session['last_played'] == winner.url:
			winner = Songs.query.filter_by(id=runnerUp).first() 
		else:
			winner.play_count += 1
			db.session.commit()
			if not winner:
                                playlistRandomizer(userid,playlist_id)
                        else:
                                return winner

	except Exception, e:
		print e
		pass
                if not winner:
                        playlistRandomizer(userid,playlist_id)
                else:
                        winner.play_count += 1
                        db.session.commit()
                        return winner
	
def playlistRandomizerBiased(userid,playlist_id):
	songs = Songs.query.filter_by(playlist_id=playlist_id).all()
	if len(songs) == 1:
                for song in songs:
                        song.play_count += 1
                        db.session.commit()
                        return song
	largestValue = 0
	secondLargestValue = 0
	currentWinner = 0
	runnerUp = 0
	for song in songs:
		randomNumber = random.randint(1,100)
		holder = int(song.weight) * randomNumber
		if song.play_count != 0:
			holder = holder / int(song.play_count)
		if holder > largestValue:
			largestValue = holder
			currentWinner = song.id
		if holder <= largestValue and holder > secondLargestValue:
			secondLargestValue = holder
			runnerUp = song.id
		winner = Songs.query.filter_by(id=currentWinner).first()
	try:
		if winner.suppress == 1:
			winner.suppress = 0
                        db.session.commit()
                        winner = Songs.query.filter_by(id=runnerUp).first()
		elif session['last_played'] == winner.url:
			winner = Songs.query.filter_by(id=runnerUp).first() 
		else:
			winner = Songs.query.filter_by(id=currentWinner).first()
			winner.play_count += 1
			db.session.commit()
			if not winner:
				playlistRandomizerBiased(userid,playlist_id)
			else:
				return winner

	except:
		pass
		if not winner:
                	playlistRandomizerBiased(userid,playlist_id)
                else:
                	winner.play_count += 1
                	db.session.commit()
			return winner


# Takes youtube video ID, returns duration of video
def getDuration(url):
	requestString = 'https://gdata.youtube.com/feeds/api/videos/%s?v=2&alt=jsonc' % str(url)
	r = requests.get(requestString)
	json = r.json()
	duration = json['data']['duration']
	return duration

# Takes youtube video ID, returns title of video
def getTitle(url):
	requestString = 'https://gdata.youtube.com/feeds/api/videos/%s?v=2&alt=jsonc' % str(url)
	r = requests.get(requestString)
	json = r.json()
	title = json['data']['title']
	return title

# Fetches JSON object
def getJSON(url):
	requestString = 'https://gdata.youtube.com/feeds/api/playlists/%s?v=2&alt=json' % str(url)
	r = requests.get(requestString)
	json = r.json()
	return json

def getTitleHash(title):
	m = md5.new()
        m.update(title)
	return m.hexdigest()
	

# Takes URL returns video id of youtube video
def video_id(value):
    query = urlparse(value)
    if query.hostname == 'youtu.be':
        return query.path[1:]
    if query.hostname in ('www.youtube.com', 'youtube.com'):
        if query.path == '/watch':
            p = parse_qs(query.query)
            return p['v'][0]
        if query.path[:7] == '/embed/':
            return query.path.split('/')[2]
        if query.path[:3] == '/v/':
            return query.path.split('/')[2] 
    return value

def getSoundcloudDuration(video_id):
	if video_id:
		requestString = 'https://api.soundcloud.com/tracks/%s.json?client_id=a70dfb8797323f05d0e00bc6ffad3146' % str(video_id)	
		r = requests.get(requestString)
		json = r.json()
		duration = json['duration'] / 1000
		return duration
	else:
		return None

def getSoundcloudAlbumArt(video_id):
	if video_id:
		requestString = 'https://api.soundcloud.com/tracks/%s.json?client_id=a70dfb8797323f05d0e00bc6ffad3146' % str(video_id)
		r = requests.get(requestString)
                json = r.json()
                albumart = json['duration'] / 1000
                return albumart
	else:
		return None
'''
	Endpint / route definitions
'''

#
# TEST ENDPOINTS
#

@app.route('/preregister', methods=['POST'])
def preregister():
	try:
		if request.form['email']:
			return render_template('register.html', email=request.form['email'])
		else:
			return render_template('index.html', error="Sorry, something happened there!")
	except Exception, e:
		print e
		return render_template('index.html', error="Sorry, something happened there!")

@app.route('/landing')
def landing():
	return render_template('landing/index.html');

@app.route('/search')
def search():
	return render_template('search.html')

@app.route('/search/<query>', methods=['GET'])
@app.route('/search/handler', methods=['POST'])
def searchHandler(query=0):
	try:
		if query != 0 and session['logged_in']:
			allPlaylists = Playlist.query.filter_by(user_id=session['id']).all()
			allTags = Tags.query.filter_by(user_id=session['id']).all()
			allSongs = Songs.query.filter_by(user_id=session['id']).all()
			playlistResults = []
			tagResults = []
			songResults = []
			for playlist in allPlaylists:
				if str(query).lower() in str(playlist.title).lower():
					playlistResults.append(playlist)
			for song in allSongs:
				if str(query).lower() in str(song.title).lower():
					songResults.append(song)
				if str(query).lower() in str(song.url).lower():
					songResults.append(song)
			for tag in allTags:
				if str(query).lower() in str(tag.tag_name).lower():
					tagResults.append(tag)
			return render_template('search.html', songs=songResults, tags=tagResults, playlists=playlistResults)
		elif request.form['search'] and session['logged_in']:
			allPlaylists = Playlist.query.filter_by(user_id=session['id']).all()
                        allTags = Tags.query.filter_by(user_id=session['id']).all()
                        allSongs = Songs.query.filter_by(user_id=session['id']).all()
                        playlistResults = []
                        tagResults = []
                        songResults = []
                        for playlist in allPlaylists:
                                if str(request.form['search']).lower() in str(playlist.title).lower():
                                        playlistResults.append(playlist)
                        for song in allSongs:
                                if str(request.form['search']).lower() in str(song.title).lower():
                                        songResults.append(song)
                                if str(request.form['search']) in str(song.url).lower():
                                        songResults.append(song)
                        for tag in allTags:
                                if str(request.form['search']).lower() in str(tag.tag_name).lower():
                                        tagResults.append(tag)
			return render_template('search.html', songs=songResults, tags=tagResults, playlists=playlistResults)
	except Exception, e:
		print e
		return render_template('index.html', error="Sorry, something went wrong there, try again!")

#
# ERROR PAGE ENDPOINTS
#

@app.errorhandler(404)
def page_not_found(e):
	return render_template('404.html'), 404

#
# ADMIN ENDPOINTS	
#

@app.route('/admin/admin/edit/<admin_id>/handler', methods=['POST'])
def adminAdminEditHandler(admin_id):
        try:
                if session['is_admin']:
                        admin = Admin.query.filter_by(id=admin_id).first()
			if request.form['username']:
				admin.username = request.form['username']
			if request.form['password']:
				admin.password = hashPassword(request.form['password'])
			db.session.commit()
                        return redirect('/admin')
                else:
                        return render_template('index.html', error="You probably shouldn't be here")
        except Exception, e:
                print e
                return render_template('index.html', error="You probably shouldn't be here")

@app.route('/admin/admin/edit/<admin_id>')
def adminAdminEdit(admin_id):
        try:
                if session['is_admin']:
                        admin = Admin.query.filter_by(id=admin_id).first()
                        return render_template('edit_admin.html', admin=admin)
                else:
                        return render_template('index.html', error="You probably shouldn't be here")
        except Exception, e:
                print e
                return render_template('index.html', error="You probably shouldn't be here")

@app.route('/admin/user/<user_id>/reset')
def adminUserReset(user_id):
        try:
                if session['is_admin']:
                        you = UsersDev.query.filter_by(id=user_id).first()
			if you:
				reset = getResetURL(10)
				you.reset_url = reset
				db.session.commit()
				msg = Message("mixr - Password Reset Request",
						sender="mixr <donotreply@mixr.pw>",
						recipients=[you.email])
				msg.html = "<h3>A little birdy told us you forgot your password!</h3><p>Don't worry, this is the email we mentioned on the reset page. Go ahead and click the link below to reset your password:</p><a href=\"https://www.mixr.pw/forgot/%s\">Reset Password</a>" % str(reset)
				mail.send(msg)
				return redirect('/admin')
                else:
                        return render_template('index.html', error="You probably shouldn't be here")
        except Exception, e:
                print e
                return render_template('index.html', error="You probably shouldn't be here")

@app.route('/admin/admin/delete/<admin_id>')
def adminAdminDeleteHandler(admin_id):
        try:
                if session['is_admin']:
                        admin = Admin.query.filter_by(id=admin_id).first()
			db.session.delete(admin)
			db.session.commit()
			return redirect('/admin')
                else:
                        return render_template('index.html', error="You probably shouldn't be here")
        except Exception, e:
                print e
                return render_template('index.html', error="You probably shouldn't be here")

@app.route('/admin/admin/create/handler', methods=['POST'])
def adminAdminCreateHandler():
        try:
                if session['is_admin'] and request.form['username'] and request.form['password']:
                        newAdmin = Admin(request.form['username'], hashPassword(request.form['password']))
			db.session.add(newAdmin)
			db.session.commit()
			return redirect('/admin')
                else:
                        return render_template('index.html', error="You probably shouldn't be here")
        except Exception, e:
                print e
                return render_template('index.html', error="You probably shouldn't be here")

@app.route('/admin/admin/create')
def adminAdminCreate():
	try:
		if session['is_admin']:
			return render_template('admin_create_admin.html')
		else:
			return render_template('index.html', error="You probably shouldn't be here")
	except Exception, e:
		print e
		return render_template('index.html', error="You probably shouldn't be here")

@app.route('/admin/user/delete/<user_id>')
def adminUserDeleteHandler(user_id):
	try:
		if session['is_admin']:
			you = UsersDev.query.filter_by(id=user_id).first()
			db.session.delete(you)
			db.session.commit()
			return redirect('/admin')
		else:
			return render_template('index.hmtl', error="You probably shouldn't be here")
	except Exception, e:
		print e
		return render_template('index.hmtl', error="You probably shouldn't be here")

@app.route('/admin/user/edit/<user_id>/handler', methods=['POST'])
def adminUserEditHandler(user_id):
	try:
		if session['is_admin']:
			you = UsersDev.query.filter_by(id=user_id).first()
			if request.form['username']:
				you.username = request.form['username']
			if request.form['password']:
				newPassword = hashPassword(request.form['password'])
				you.password = newPassword
			if request.form['email']:
				you.email = request.form['email']
			if request.form['algorithim']:
				if request.form['algorithim'] == "default":
					if you.random_type != 0:
						you.random_type = 0
						session['random_type'] = 0
				else:
					if you.random_type != 1:
						you.random_type = 1
						session['random_type'] = 1
			db.session.commit()
			return redirect('/admin')
	except Exception, e:
		print e
		return render_template('index.html', error="You probably shouldn't be here")

@app.route('/admin/user/edit/<user_id>')
def adminUserEdit(user_id):
	try:
		if session['is_admin']:
			user = UsersDev.query.filter_by(id=user_id).first()
			return render_template('edit_user.html', user=user)
		else:
			return render_template('index.html', error="You probably shouldn't be here")
	except Exception, e:
		print e
		return render_template('index.html', error="You probably shouldn't be here")

@app.route('/admin/user/create/handler', methods=['POST'])
def adminUserCreateHandler():
	try:
                if session['is_admin']:
                        if request.form['username'] and request.form['password'] and request.form['email']:
				newUser = UsersDev(request.form['username'], request.form['email'], hashPassword(request.form['password']))
				db.session.add(newUser)
				db.session.commit()
				return redirect('/admin')
                else:
                        return render_template('index.html', error="You probably shouldn't be here.")
        except Exception, e:
                print e
                return render_template('admin.html', error="Something broke %s" % e)

@app.route('/admin/user/create')
def adminUserCreate():
	try:
		if session['is_admin']:
			return render_template('admin_create_user.html')
		else:
			return render_template('index.html', error="You probably shouldn't be here.")
	except Exception, e:
		print e
		return render_template('admin.html', error="Something broke %s" % e)

@app.route('/admin/login')
def adminPageLogin():
	try:
		return render_template('admin_login.html')
	except Exception, e:	
		print e
		return render_template('index.html', error="You probably shouldn't be there!")

@app.route('/admin/login/handler', methods=['POST','GET'])
def adminPageLoginHandler():
	try:
		if request.form['username'] and request.form['password']:
			passwordHash = hashPassword(request.form['password'])			
			you = Admin.query.filter_by(username=request.form['username'],password=passwordHash).first()
			if you:
				session['username'] = you.username
				session['is_admin'] = True
				return redirect('/admin')
			else:
				return render_template('admin_login.html', error="Invalid credentials")
	except Exception, e:
		print e
		print "Happened at login"
		return render_template('index.html', error="You probably shouldn't be there!")

@app.route('/admin')
def adminPage():
	try:
		if session['username'] and session['is_admin']:
			allUsers = UsersDev.query.all()
			allPlaylists = Playlist.query.all()
			allSongs = Songs.query.all()
			allAdmins = Admin.query.all()
			return render_template('admin.html', users=allUsers, playlists=allPlaylists, songs=allSongs, admins=allAdmins)
		else:
			return render_template('index.html', error="You probably shouldn't be there!")
	except Exception, e:
		print e
		print "Happened on page render"
		return render_template('index.html', error="You probably shouldn't be there!")

#
# TAG ENDPOINTS
#

@app.route('/tag/<tag_id>')
def tagSearch(tag_id):
	try:
		if session['logged_in'] and tag_id:
			playlists = []
			songs = []
			tag = Tags.query.filter_by(user_id=session['id'],id=tag_id).first()
			allTags = Tags.query.filter_by(user_id=session['id'],tag_name=tag.tag_name).all()
			for tag in allTags:
				if tag.playlist_id > 0:
					playlist = Playlist.query.filter_by(id=tag.playlist_id,user_id=session['id']).first()
					playlists.append(playlist)
				if tag.song_id > 0:
					song = Songs.query.filter_by(id=tag.song_id,user_id=session['id']).first()
					songs.append(song)
			return render_template('tags.html',playlists=playlists, songs=songs, tag=tag)
	except Exception, e:
		print e
		return render_template('index.html',error="Something went wrong there, try again!")

@app.route('/playlist/<playlist_id>/tag/<tag_id>/delete')
def playlistDeleteTag(playlist_id, tag_id):
	try:
		if playlist_id and tag_id and session['logged_in']:
			playlist = Playlist.query.filter_by(user_id=session['id'],id=playlist_id).first()
			if playlist:
				tag = Tags.query.filter_by(id=tag_id,user_id=session['id']).first()
				db.session.delete(tag)
				db.session.commit()
				return redirect('/playlist')
	except Exception, e:
		return render_template('index.html', error="Something went wrong there, try again!")

@app.route('/song/<song_id>/tag/<tag_id>/delete')
def songDeleteTag(song_id, tag_id):
        try:
                if song_id and tag_id and session['logged_in']:
                        song = Songs.query.filter_by(user_id=session['id'],id=song_id).first()
                        if song:
                                tag = Tags.query.filter_by(id=tag_id,user_id=session['id']).first()
                                db.session.delete(tag)
                                db.session.commit()
                                return redirect('/playlist')
        except Exception, e:
                return render_template('index.html', error="Something went wrong there, try again!")

@app.route('/playlist/<playlist_id>/tag/add')
def playlistTagAdd(playlist_id):
	try:
		if session['logged_in']:
			return render_template('add_tag.html', tag_type="playlist", playlist_id=playlist_id)
	except Exception, e:
		print e
		return render_template('index.html',error="Something went wrong there, try again!")

@app.route('/song/<song_id>/tag/add')
def songTagAdd(song_id):
        try:
                if session['logged_in']:
                        return render_template('add_tag.html', tag_type="song", song_id=song_id)
        except:
                return render_template('index.html',error="Something went wrong there, try again!")

@app.route('/playlist/<playlist_id>/tag/add/handler',methods=['POST'])
def playlistTagAddHandler(playlist_id):
	try:
		if session['logged_in'] and playlist_id and request.form['tag_title']:
			playlistVerify = Playlist.query.filter_by(user_id=session['id'],id=playlist_id).first()
			if playlistVerify:
				newTag = Tags(session['id'],request.form['tag_title'],playlist_id=playlist_id)
				db.session.add(newTag)
				db.session.commit()
				return redirect('/playlist')
			else:
				return render_template('index.html', error="This isn't your playlist, you can't add tags to somebody elses playlist.")
	except Exception, e:
		print e
		return render_template('index.html',error="Something went wrong there, try again!")

@app.route('/song/<song_id>/tag/add/handler',methods=['POST'])
def songTagAddHandler(song_id):
        try:
                if session['logged_in'] and song_id and request.form['tag_title']:
                        songVerify = Songs.query.filter_by(user_id=session['id'],id=song_id).first()
                        if songVerify:
                                newTag = Tags(session['id'],request.form['tag_title'],song_id=song_id)
                                db.session.add(newTag)
                                db.session.commit()
                                return redirect('/playlist')
                        else:
                                return render_template('index.html', error="This isn't your song, you can't add tags to somebody elses playlist.")
        except Exception, e:
                print e
                return render_template('index.html',error="Something went wrong there, try again!")

#
# GENERIC PAGE ENDPOINTS
#

@app.route('/')
def index():
	session.permanent = True
	try:
		try:
			if request.cookies.get('first_time'):
				try:
					if session['logged_in'] == True:
	                                	return render_template('index.html',loggedin=True)
	                        except Exception ,e:
	                                return render_template('index.html',loggedin=False)
			else:
	                        resp = make_response(render_template('landing/index.html'))
	                        resp.set_cookie('first_time','0')
	                        return resp
		except Exception, e:
			print e
			resp = make_response(render_template('landing/index.html'))
                        resp.set_cookie('first_time','0')
                        return resp
	except Exception, e:
		return render_template('index.html',loggedin=False)

@app.route('/privacy')
def privacy():
	return render_template('privacy.html')

@app.route('/register')
def register():
	return render_template('register.html')

@app.route('/account')
def account():
	try:
		if session['logged_in']:
			return render_template('account.html',username=session['username'],email=session['email'],random_type=session['random_type'])
	except Exception, e:
		print e
		return render_template('index.html',error="You need to be logged in to view the account page.")

@app.route('/account/handler',methods=['POST','GET'])
def accountHandler():
	try:
		if session['logged_in'] and request.method == "POST":
			you = UsersDev.query.filter_by(username=session['username'],id=session['id'],email=session['email']).first()
			if request.form['password'] and request.form['password_again']:
				if request.form['password'] == request.form['password_again']:
					newPassword = hashPassword(request.form['password'])
					you.password = newPassword
				else:
					return render_template('account.html',username=session['username'],email=session['email'],error="The passwords you entered did not match.")
			
			if request.form['email']:
				you.email = request.form['email']
				session['email'] = request.form['email']
			
			if request.form['algorithim']:
				if request.form['algorithim'] == "default":
					if you.random_type != 0:
						you.random_type = 0
						session['random_type'] = 0
				else:
					if you.random_type != 1:
						you.random_type = 1
						session['random_type'] = 1
			db.session.commit()
			return render_template('account.html',username=session['username'],email=session['email'],random_type=session['random_type'],message="Changes saved.")
	except Exception, e:
		return render_template('account.html',username=session['username'],email=session['email'],error="Sorry, something happened there, try again!")

@app.route('/about')
def about():
	return render_template('about.html')

@app.route('/faq')
def faq():
	return render_template('faq.html')

@app.route('/contact')
def contact():
	return render_template('contact.html')

@app.route('/register/handler', methods=['POST','GET'])
def registerHandler():
	if request.method == "POST":
		if request.form['username'] and request.form['email'] and request.form['password']:
			if request.form['password'] == request.form['password_again']:
				username = request.form['username']
				email = request.form['email']
				password = request.form['password']
				passwordHash = hashPassword(password)
				newUser = UsersDev(username, email, passwordHash)
			        try:
					db.session.add(newUser)
				        db.session.commit()
				except:
					print e
                                        if 'Duplicate' in e.message:
                                                return render_template('register.html', error="Sorry, that username or email is already in use, can you try another?")
					return render_template('register.html', error="Something went wrong, try again")
			else:
				return render_template('register.html',error="Your passwords did not match")
				# return an error saying the passwords didn't match
		else:
			return render_template('register.html',error="You didn't fill out the entire form")
			#return an error saying something wasn't filled out
	else:
		return render_template('register.html')
		# redirect back to register.html

	session['username'] = request.form['username']
	you = UsersDev.query.filter_by(username=request.form['username']).first()
	session['id'] = you.id
	session['logged_in'] = True
	session['random_type'] = 1
	return render_template('index.html', message="Congrats %s, you are now registered and logged in!" % session['username'])

#
# LOGIN RELATED ENDPOINTS
#

@app.route('/login')
def login():
	if session['logged_in']:
		return redirect('/playlist')
	else:
		return render_template('login.html')

@app.route('/logout')
def logout():
	session.pop('logged_in', None)
	session.pop('username', None)
	session.pop('id', None)
	flash('You were logged out')
	return redirect(url_for('index'))

@app.route('/login/handler', methods=['POST','GET'])
def loginHandler():
	try:
		if request.method == "POST":
			if request.form['username'] and request.form['password']:
				username = request.form['username']
				password = request.form['password']
				passwordHash = hashPassword(password)
					
				you = UsersDev.query.filter_by(username=username, password=passwordHash).first()
				if you.id:
					session['username'] = username
					session['id'] = you.id
					session['logged_in'] = True
					session['email'] = you.email
					session['random_type'] = you.random_type
					return redirect(url_for('index'))
				else:
					return render_template('login.html', error="Invalid credentials")
			else:
				return render_template('login.html', error="You did not provide a username and password")
		else:
			return render_template('login.html', error="Invalid method")
	except Exception, e:
		print e
		if e.message == "'NoneType' object has no attribute 'id'":
			return render_template('login.html', error="Invalid credentials, try again.")
		else:
			return render_template('login.html', error="Sorry, something went wrong there, try again!")

@app.route('/forgot')
def forgot():
	return render_template('forgot.html')

@app.route('/forgot/handler', methods=['POST','GET'])
def forgotHandler():
	try:
		if request.method == "POST" and request.form['username'] and request.form['email']:
			you = UsersDev.query.filter_by(username=request.form['username'],email=request.form['email']).first()
			if you:
				reset = getResetURL(10)
				you.reset_url = reset
				you.reset_expiration = datetime.datetime.now()
				db.session.commit()
				msg = Message("mixr - Password Reset Request",
						sender="mixr <donotreply@mixr.pw>",
						recipients=[you.email])
				msg.html = "<h3>A little birdy told us you forgot your password!</h3><p>Don't worry, this is the email we mentioned on the reset page. Go ahead and click the link below to reset your password:</p><a href=\"https://www.mixr.pw/forgot/%s\">Reset Password</a>" % str(reset)
				mail.send(msg)
				return render_template('forgot.html',message="If those credentials matched a user, you'll get an email in a moment with more information")
			else:
				return render_template('forgot.html',message="If those credentials matched a user, you'll get an email in a moment with more information")
	except Exception, e:
		print "I caught an error: %s" % str(e)
		return render_template('forgot.html', error="Sorry, something went wrong there, try again!")	

@app.route('/forgot/<reset_id>')
def resetURL(reset_id):
	try:
		if reset_id:
			you = UsersDev.query.filter_by(reset_url=reset_id).first()
			if you:
				return render_template("reset.html", token=reset_id)
			else:
				return render_template("forgot.html", error="That isn't a valid reset token, try again.")
	except Exception, e:
		print "I caught an error: %s" % str(e)
                return render_template('forgot.html', error="Sorry, something went wrong there, try again!")

@app.route('/forgot/<reset_id>/handler', methods=['POST','GET'])
def resetURLHandler(reset_id):
	try:
		if reset_id and request.form['password'] and request.form['password_again']:
			password = request.form['password']
			password_again = request.form['password_again']
			if password == password_again:
				passwordHashed = hashPassword(password)
				you = UsersDev.query.filter_by(reset_url=reset_id).first()
				now = datetime.datetime.now()
				diff = now - datetime.datetime.strptime(you.reset_expiration, '%Y-%m-%d %X')
				totalMinutes = diff.total_seconds() / 60
				if totalMinutes > 10:
					you.reset_url = ""
					you.reset_expiration = ""
					db.session.commit()
					return render_template('forgot.html', error="Your reset code has expired, please try again.")
				else:
					you.password = passwordHashed
					you.reset_url = ""
					db.session.commit()
					return render_template("index.html", message="Password successfully reset.")
			else:
				return redirect('/forgot/%s/handler') % str(reset_id)
	except Exception, e:
                print "I caught an error: %s" % str(e)
                return render_template('forgot.html', error="Sorry, something went wrong there, try again!")

#
# PLAYLIST RELATED ENDPOINTS
#

@app.route('/playlist/copy/<playlist_id>')
def playlistCopy(playlist_id):
	try:
		if session['logged_in'] and playlist_id:
			toCopy = Playlist.query.filter_by(id=playlist_id).first()
			if toCopy.public == 1:
				newPlaylist = Playlist(session['id'], toCopy.title, toCopy.public, toCopy.hash_value)
				db.session.add(newPlaylist)
				db.session.commit()
				newPlaylist = Playlist.query.filter_by(user_id=session['id'], title=toCopy.title).first()
				songsToCopy = Songs.query.filter_by(playlist_id=playlist_id).all()
				for song in songsToCopy:
					print song.title
					newSong = Songs(newPlaylist.id, session['id'], song.url, song.weight, song.title, 0)
					db.session.add(newSong)
					newPlaylist.numSongs += 1
				db.session.commit()
				return redirect('/playlist')
			else:
				return render_template('index.html', error="That isn't your playlist, you can't copy it.")
	except Exception, e:
		print e
		return render_template('index.html', error="Sorry, something went wrong there, try again!")

@app.route('/playlist/<playlist_id>/<song_id>/up',methods=['POST','GET'])
def upvote(playlist_id,song_id):
	try:
		if session['logged_in'] and playlist_id and song_id:
			song = Songs.query.filter_by(id=song_id,user_id=session['id']).first()
			if song:
				if song.weight == 5:
					# Do nothing, that's the max
					return redirect('/playlist/play/%s' % str(playlist_id))
				else:
					song.weight = song.weight + 1
					db.session.commit()
					return redirect('/playlist/play/%s' % str(playlist_id))
			else:
				return redirect('/playlist/play/%s' % str(playlist_id))		
	except Exception, e:
		print e
		return redirect('/playlist/play/%s' % str(playlist_id))

@app.route('/playlist/<playlist_id>/<song_id>/down',methods=['POST','GET'])
def downvote(playlist_id,song_id):
        try:
                if session['logged_in'] and playlist_id and song_id:
                        song = Songs.query.filter_by(id=song_id,user_id=session['id']).first()
                        if song:
                                if song.weight == 1:
                                        # Do nothing, that's the minimum
                                        return redirect('/playlist/play/%s' % str(playlist_id))
                                else:
                                        song.weight = song.weight - 1
					print "New weight: %s" % str(song.weight)
                                        db.session.commit()
                                        return redirect('/playlist/play/%s' % str(playlist_id))
                        else:
                                return redirect('/playlist/play/%s' % str(playlist_id))
        except Exception, e:
                print e
                return render_template('/playlist/play/%s' % str(playlist_id), error="Sorry, something went wrong there, try again!")

@app.route('/playlist/play/<path:playlist_id>/last')
def playlistPlayLast(playlist_id):
	try:
		if session['logged_in'] and session['last_played']:
			duration = getDuration(session['last_played'])
			title = getTitle(session['last_played'])
			song = Songs.query.filter_by(url=session['last_played']).first()
			return render_template('play.html', duration=duration, title=title, playlist_id=playlist_id, video_to_play=session['last_played'], lastplayed=True,song=song)
	except Exception, e:
		print e
		return redirect('/playlist/play/%s' % str(playlist_id))

@app.route('/playlist/setlast/<playlist_id>/<video_id>')
def setLast(playlist_id,video_id):
	try:
		if playlist_id and video_id and session['logged_in']:
			session['last_played'] = video_id
			return redirect('/playlist/play/%s' % str(playlist_id))
		else:
			return redirect('/playlist/play/%s' % str(playlist_id))
	except:
		return redirect('/playlist/play/%s' % str(playlist_id))

@app.route('/playlist/play/<playlist_id>')
def playlistPlay(playlist_id):
	try:
		if session['logged_in'] and session['random_type'] == 0:
			playlistVerify = Playlist.query.filter_by(user_id=session['id']).all()
			flag = 0
			for playlists in playlistVerify:
				if playlists.id == int(playlist_id):
					flag = 1
			if flag == 1:
				winner = playlistRandomizer(session['id'],playlist_id)
				while winner is None:
                                        winner = playlistRandomizer(session['id'],playlist_id)
				playlist = Playlist.query.filter_by(id=playlist_id).first()
				if playlist.public == 1:
					ispublic = 1
				else:
					ispublic = 0
				notyours = 0
				return render_template('play.html', video_to_play=winner.url,title=winner.title, playlist_id=playlist_id, song=winner, notyours=notyours, ispublic=ispublic)
			else:
				playlist = Playlist.query.filter_by(id=playlist_id).first()
				if playlist.public == 1:
					if playlist.user_id == session['id']:
						notyours = 0
					else:
						notyours = 1 
                                	winner = playlistRandomizer(session['id'],playlist_id)
					while winner is None:
                                        	winner = playlistRandomizerBiased(session['id'],playlist_id)
					ispublic = 1
					return render_template('play.html', video_to_play=winner.url,title=winner.title, playlist_id=playlist_id, song=winner, notyours=notyours, ispublic=ispublic)
				else:
					playlists = Playlist.query.filter_by(user_id=session['id']).all()
					return render_template('playlist.html', error="This is not your playlist, you can only listen to your playlists.",playlists=playlists)
		elif session['logged_in'] and session['random_type'] == 1:
			playlistVerify = Playlist.query.filter_by(user_id=session['id']).all()
                        flag = 0
                        for playlists in playlistVerify:
                                if playlists.id == int(playlist_id):
                                        flag = 1
                        if flag == 1:
                                winner = playlistRandomizerBiased(session['id'],playlist_id)
				while winner is None:
					winner = playlistRandomizerBiased(session['id'],playlist_id)
				playlist = Playlist.query.filter_by(id=playlist_id).first()
				if playlist.public == 1:
                                        ispublic = 1
                                else:
                                        ispublic = 0
                                notyours = 0
				return render_template('play.html', video_to_play=winner.url,title=winner.title, playlist_id=playlist_id, song=winner, notyours=notyours, ispublic=ispublic)
                        else:
				if playlist.public == 1:
					if playlist.user_id == session['id']:
                                                notyours = 0
                                        else:
                                                notyours = 1
                                        winner = playlistRandomizerBiased(session['id'],playlist_id)
					while winner is None:
                                        	winner = playlistRandomizerBiased(session['id'],playlist_id)
					ispublic = 1
					return render_template('play.html', video_to_play=winner.url,title=winner.title, playlist_id=playlist_id, song=winner, isyours=isyours, ispublic=ispublic)
                                else:
                                        playlists = Playlist.query.filter_by(user_id=session['id']).all()
                                        return render_template('playlist.html', error="This is not your playlist, you can only listen to your playlists.",playlists=playlists)

		else:
			return render_template('index.html', error="You are not logged in, please log in and try again.")
	except Exception, e:
		print e
		return render_template('index.html', error="Sorry, something broke there, try again!")

@app.route('/play/loop')
@app.route('/play/loop/')
@app.route('/play/loop/<path:video_id>')
def playLoop(video_id=None):
	try:
		# Endpoint that will play a Youtube video either once, or on a loop
		if video_id:
			title = getTitle(video_id)
			duration = getDuration(video_id)
			return render_template('play_single.html', video_id=video_id, loop=1, duration=duration)
		else:
			return render_template('index.html', error="That video ID is not valid, try again.")
	except:
		return render_template('index.html', error="Sorry, something broke there, try again!")

@app.route('/play/once')
@app.route('/play/once/')
@app.route('/play/once/<path:video_id>')
def playOnce(video_id=None):
	try:
	        if video_id:
			video_to_play = video_id
			title = getTitle(video_id)
			return render_template('play_single.html', video_to_play=video_to_play, title=title)
		else:
			return render_template('index.html', error="That video ID is not valid, try again.")
	except:
		return render_template('index.html', error="Sorry, something broke there, try again!")

@app.route('/playlist/create/handler', methods=['POST','GET'])
def playlistHandler():
	try:
		if request.method == "POST" and session['logged_in']:
			title = request.form['name']
			try:
				public = request.form['public']
				public = 1
			except:
				public = 0
				pass
			playlistHash = getTitleHash(title)
			newPlaylist = Playlist(session['id'], title, public, playlistHash)
			try:
				db.session.add(newPlaylist)
				db.session.commit()
			except:
				return render_template('create_playlist.html', error="Sorry, something went wrong there, try again!")
			playlists = Playlist.query.filter_by(user_id=session['id'])
			return render_template('playlist.html', playlists=playlists)
		else:
			return render_template('index.html', error="You are not logged in, please log in and try again.")
	except Exception, e:
		print e
		return render_template('index.html', error="Sorry, something went wrong there, try again!")
		
@app.route('/playlist/create')
def playlistCreate():
	try:
		if session['logged_in']:
			return render_template('create_playlist.html')
		else:
			return render_template('index.html', error="You are not logged in, please log in and try again.")
	except:
		return render_template('index.html', error="Sorry, something went wrong there, try again!")

@app.route('/playlist/delete/<playlist_id>')
def playlistDelete(playlist_id):
	try:
		if playlist_id and session['logged_in']:
			playlists = Playlist.query.filter_by(user_id=session['id'],id=playlist_id).first()
			if playlists.id:
				db.session.delete(playlists)
				songs = Songs.query.filter_by(user_id=session['id'],playlist_id=playlist_id).all()
				for song in songs:
					db.session.delete(song)
				db.session.commit()
				playlists = Playlist.query.filter_by(user_id=session['id']).all()
				tags = Tags.query.filter_by(user_id=session['id']).all()
				return render_template('playlist.html',playlists=playlists,message="Playlist successfully deleted.", tags=tags)	
			else:
				playlists = Playlist.query.filter_by(user_id=session['id']).all()
				return render_template('playlist.html',error="That does not appear to be your playlist, you can't delete playlists other than your own.",playlists=playlists)
		else:
			return render_template('index.html', error="You are not logged in, please log in and try again.")	
	except Exception, e:
		playlists = Playlist.query.filter_by(user_id=session['id']).all()
		return render_template('playlist.html', error="Sorry, something went wrong there, try again!",playlists=playlists)

@app.route('/playlist/add/<playlist_id>', methods=['POST', 'GET'])
def playlistAddSong(playlist_id):
	try:
		if session['logged_in']:
			return render_template('add_song.html', playlist_id=playlist_id)
		else:
			return render_template('index.html', error="You are not logged in, please log in and try again.")
	except:
		return render_template('index.html', error="You are not logged in, please log in and try again.")

@app.route('/playlist/add/<playlist_id>/handler', methods=['POST','GET'])
def addSongHandler(playlist_id):
	try:
		if request.method == "POST" and session['logged_in'] and playlist_id:
			if request.form['url'] and request.form['title']:
				verify = Playlist.query.filter_by(id=playlist_id,user_id=session['id']).first()
				if request.form['weight']:
					weight = request.form['weight']
				else:
					weight = 3
				if verify:
					title = request.form['title']
					try:
						test = int(weight)
						if test < 0 or test > 5:
							return render_template('add_song.html', error="Please enter a weight between 1 and 5", playlist_id=playlist_id)
					except:
						return render_template('add_song.html', error="Please enter a numeric value between 1 and 5 for the weight", playlist_id=playlist_id)
					url = request.form['url']
					parsedURL = video_id(url)
					playlist = Playlist.query.filter_by(id=playlist_id).first()
					if playlist.id:
						newSong = Songs(playlist_id, session['id'], parsedURL, weight, request.form['title'], 0)
						db.session.add(newSong)
						playlist.numSongs += 1
						db.session.commit()
						redirectString = "/playlist/%s" % str(playlist_id)
						return redirect(redirectString)
					else:
						return render_template('add_song.html', error="Provided incorrect playlist ID")
				else:
					return render_template('add_song.html', error="This isn't your playlist")
			else:
				return render_template('add_song.html', error="You didn't fill out all of the fields")
		else:
			return render_template('add_song.html')
	except Exception, e:
		return render_template('index.html', error="You are not logged in, please log in and try again.")

@app.route('/song/edit/<song_id>')
def songEdit(song_id):
	try:
		if session['logged_in']:
			song = Songs.query.filter_by(id=song_id, user_id=session['id']).first()
			if song:
				return render_template('edit_song.html',song_id=song_id, song=song)
			else:
				playlists = Playlist.query.filter_by(user_id=session['id']).all()
				return render_template('playlist.html',playlists=playlists,error="This is not your song, you can only edit your own songs")
		else:
			return render_template('index.html', error="You are not logged in, please log in and try again.")
	except:
		return render_template('index.html', error="You are not logged in, please log in and try again.")

@app.route('/song/edit/<song_id>/handler', methods=['POST','GET'])
def songEditHandler(song_id):
	try:
		if session['logged_in']:
			song = Songs.query.filter_by(id=song_id, user_id=session['id']).first()
			if request.form['url']:
				song.url = request.form['url']
			if request.form['title']:
				song.title = request.form['title']
			if request.form['weight']:
				song.weight = request.form['weight']
			db.session.commit()
			redirectString = "/playlist/%s" % str(song.playlist_id)
			return redirect(redirectString)
		else:
			redirectString = "/song/edit/%s" % str(song_id)
			return render_template('index.html', error="You are not logged in, please log in and try again.")
	except:
		return render_template('index.html', error="You are not logged in")

@app.route('/playlist')
def playlistList():
	try:
		if session['logged_in']:
			tags = Tags.query.filter_by(user_id=session['id']).all()
			playlists = Playlist.query.filter_by(user_id=session['id']).all()
			return render_template('playlist.html', playlists=playlists, tags=tags)
		else:
			return render_template('index.html', error="You are not logged in, please log in and try again.")
	except:
		return render_template('index.html', error="You are not logged in")

@app.route('/playlist/<playlist_id>')
def playlistView(playlist_id):
	try:
		if session['logged_in']:
			playlist = Playlist.query.filter_by(id=playlist_id).first()
			if playlist.public == 1:
				songs = Songs.query.filter_by(playlist_id=playlist_id).all()
				if playlist.user_id == session['id']:
					tags = Tags.query.filter_by(user_id=session['id']).all()
					return render_template('playlist_view.html',playlist=playlist,songs=songs,public=False,tags=tags)
				else:
                                	return render_template('playlist_view.html',playlist=playlist,songs=songs,public=True)	
			else:
				if playlist.user_id == session['id']:
					tags = Tags.query.filter_by(user_id=session['id']).all()
					songs = Songs.query.filter_by(playlist_id=playlist_id, user_id=session['id']).all()
					return render_template('playlist_view.html',playlist=playlist,songs=songs,public=False,tags=tags)
				else:
					return render_template('index.html', error="You do not have permission to view this playlist.")
		else:
			return render_template('index.html', error="You are not logged in, please log in and try again.")	
	except:
		return render_template('index.html', error="You are not logged in")

@app.route('/song/delete/<song_id>')
def songDelete(song_id):
	try:
		if song_id and session['id']:
			verify = Songs.query.filter_by(user_id=session['id'], id=song_id).first()
			if verify.id:
				playlistid = verify.playlist_id
				playlist = Playlist.query.filter_by(id=playlistid).first()
				playlist.numSongs = playlist.numSongs - 1
				db.session.delete(verify)
				db.session.commit()
				redirectString = "/playlist/%s" % playlistid
				return redirect(redirectString)
			else:
				playlists = Playlist.query.filter_by(user_id=session['id']).all()
				return render_template('playlist.html',playlists=playlists, error="This is not your song, you can only delete your own songs.")
		else:
			playlists = Playlist.query.filter_by(user_id=session['id']).all()
			return render_template('playlist.html',error="You either did not provide a valid song ID, or you are not logged in.")			
	except Exception, e:
		playlists = Playlist.query.filter_by(user_id=session['id']).all()
		return render_template('playlist.html', error="Sorry, something went wrong there, try again!")	

@app.route('/playlist/edit/<playlist_id>')
def playlistEdit(playlist_id):
	try:
		if playlist_id and session['logged_in']:
			playlist = Playlist.query.filter_by(id=playlist_id,user_id=session['id']).first()
			if playlist:
				return render_template('edit_playlist.html',playlist=playlist)
			else:
				playlists = Playlist.query.filter_by(user_id=session['id']).all()
				return render_template('playlist.html',playlists=playlists,error="This is not your playlist, you can only edit your own playlists.")
		else:
			playlists = Playlist.query.filter_by(user_id=session['id']).all()
			return render_template('playlist.html', error="This is not your playlist to edit, you can only edit your own playlists.",playlists=playlists)
	except Exception, e:
		return render_template('index.html', error="Sorry, something went wrong there, try again!")

@app.route('/playlist/edit/<playlist_id>/handler', methods=['POST','GET'])
def playlistEditHandler(playlist_id):
	try:
		if playlist_id and session['logged_in']:
			playlist = Playlist.query.filter_by(id=playlist_id,user_id=session['id']).first()
			if request.form['name']:
				playlist.title = request.form['name']
				playlistHash = getTitleHash(request.form['name'])
				playlist.hash_value = playlistHash
				db.session.commit()
			try:
				if request.form['public']:
					flag = 0
					if request.form['public'] == "on":
						flag = 1
					if flag != playlist.public:
						playlist.public = flag
						db.session.commit()
			except:
				if playlist.public != 0:
					playlist.public = 0
					db.session.commit()
				pass		
			playlists = Playlist.query.filter_by(user_id=session['id']).all()
			return render_template('playlist.html',message="Playlist edited successfully.",playlists=playlists)
		else:
			playlists = Playlist.query.filter_by(user_id=session['id']).all()
			return render_template('playlist.html', error="You either did not provide a valid playlist ID, or used the wrong method.")	
	except Exception, e:
		print e
		return render_template('index.html', error="Sorry, something went wrong there, try again!")

@app.route('/playlist/import/youtube')
def importYoutube():
	try:
		if session['logged_in']:
			return render_template('import.html')
	except Exception, e:
		print e
		return render_template('index.html',error="Sorry, something wrong happened there, try again!")

@app.route('/playlist/import/youtube/handler',methods=['POST','GET'])
def importYoutubeHandler():
	try:
		if session['logged_in'] and request.form['youtube_playlist_id']:
			youtube_playlist_id = getPlaylistID(request.form['youtube_playlist_id'])
			if youtube_playlist_id is None:
				youtube_playlist_id = request.form['youtube_playlist_id']
			json = getJSON(youtube_playlist_id)
			playlistName = json['feed']['title']['$t']
			playlistHash = getTitleHash(playlistName)
			verify = Playlist.query.filter_by(title=playlistName, user_id=session['id']).first()
			try:
				if not verify.id:
					playlist = Playlist(session['id'],playlistName,0,playlistHash)
					db.session.add(playlist)
					db.session.commit()
					playlist = Playlist.query.filter_by(title=playlistName,user_id=session['id']).first()
				else:
					playlist = verify
			except:
				playlist = Playlist(session['id'],playlistName,0,playlistHash)
				db.session.add(playlist)
				db.session.commit()
                                playlist = Playlist.query.filter_by(title=playlistName,user_id=session['id']).first()
				pass
			numSongs = 0
			for entry in json['feed']['entry']:
				video_id_src = entry['content']['src']
				video_id_src = video_id(video_id_src)
				video_title = entry['title']['$t']
				weight = 3
				song = Songs(playlist.id,session['id'],video_id_src,weight,video_title,0)
				db.session.add(song)
				numSongs += 1
			playlist.numSongs = numSongs
			db.session.commit()
			playlists = Playlist.query.filter_by(user_id=session['id']).all()
			tags = Tags.query.filter_by(user_id=session['id']).all()				
			return render_template('playlist.html',message="Playlist successfully imported", playlists=playlists, tags=tags)
	except Exception, e:
		print e
		return render_template('import.html', error="Sorry, something wrong happened there, try again!")

@app.route('/playlist/<playlist_id>/suppress/<song_id>')
def suppress(playlist_id,song_id):
	try:
		if session['logged_in'] and playlist_id and song_id:
			song = Songs.query.filter_by(user_id=session['id'],playlist_id=playlist_id,url=song_id).first()
			if song:
				song.suppress = 1
				db.session.commit()
				return redirect('/playlist/play/%s' % str(playlist_id))
			else:
				return redirect('/playlist/play/%s' % str(playlist_id))
	except:
		return redirect('/playlist/play/%s' % str(playlist_id))

'''
	Starting the app
'''

if __name__ == '__main__':
	app.run(host='0.0.0.0',debug=True)
