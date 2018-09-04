#!/usr/bin/env python
from flask import Flask, request, render_template, flash, redirect, url_for, session, logging, g
import sqlite3 as sql
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps
import os.path


app = Flask(__name__)
app.secret_key='secret123'

databases = "databases.db"
dataBaseName = " "



#Index
@app.route('/')
def index():
	session.clear()
	with sql.connect(databases) as connection:

		connection.execute("CREATE TABLE IF NOT EXISTS dataBaseNames(name varchar(30) DEFAULT NULL)")

		return render_template('home.html')


@app.route('/home/<defSess>')
@app.route('/home/', defaults={'defSess': None})
def home(defSess):

	if defSess is None:
		session.clear()
		return render_template('home.html')
	else:
		defSess = defSess



		with sql.connect(databases) as connection:

			connection.execute("CREATE TABLE IF NOT EXISTS dataBaseNames(name varchar(30) DEFAULT NULL)")

			return render_template('home.html', defSess=defSess)


#Register form class
class RegisterForm(Form):

	username = StringField('Username', [validators.Length(min=4, max=25)])
	password = PasswordField('Password', [
		validators.DataRequired(),
		validators.EqualTo('confirm', message= 'Passwords do not match')
	])
	confirm = PasswordField('Confirm Password')

#User register
@app.route('/register', methods=['GET', 'POST'])
def register():
	form = RegisterForm(request.form)
	if request.method == 'POST' and form.validate():
		username = form.username.data
		password = sha256_crypt.encrypt(str(form.password.data))

		dataBaseName = select_database(username)
		setDataBaseName(dataBaseName)

		with sql.connect(databases) as connection:
			connection.execute("CREATE TABLE IF NOT EXISTS dataBaseNames(name varchar(30) DEFAULT NULL)")
			connection.execute("INSERT INTO dataBaseNames(name) VALUES(?)", (username,))

		with sql.connect(dataBaseName) as connection:
			connection.execute("CREATE TABLE IF NOT EXISTS users (userId INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,username varchar(30) DEFAULT NULL,password varchar(100) DEFAULT NULL,register_date timestamp NOT NULL DEFAULT (datetime('now', 'localtime')))")
			connection.execute("INSERT INTO users(username, password) VALUES(?,?)", (username, password))

			flash('You are now registered and can now log in', 'success')

		return redirect(url_for('login'))

	return render_template('register.html', form=form)


# User Login
@app.route('/login', methods=['GET', 'POST'])
def login():

	if request.method == 'POST':

		with sql.connect(databases) as connection:

			username = request.form['username']

			cur = connection.execute("SELECT * FROM dataBaseNames WHERE name = ?", (username,))

			result = cur.fetchone()

			if result is not None:

				setDataBaseName(username)
				dataBaseName = select_database(username)

				with sql.connect(dataBaseName) as connection:
					# Get form fields
					username = request.form['username']
					password_candidate = request.form['password']
					#name = request.form['name']
					connection.execute("CREATE TABLE IF NOT EXISTS users (userId INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,username varchar(30) DEFAULT NULL,password varchar(100) DEFAULT NULL,register_date timestamp NOT NULL DEFAULT (datetime('now', 'localtime')))")
					cur = connection.execute("SELECT * FROM users WHERE username = ?", (username,))

					result = cur.fetchone()

					if result is not None:

						data = result
						print('data[password]', data)
						password = data[2]

						#Compare Passwords
						if sha256_crypt.verify(password_candidate, password):
							#PasswordField
							session['logged_in'] = True
							session['username'] = username
							#session['name'] = name
							global defSess
							defSess = session['username']

							flash('You are now logged in', 'success')
							return redirect(url_for('memberSearch', defSess=defSess))
						else:
							error = 'Invalid Login'
							return render_template('login.html', error=error)
						#close connection
					else:
						error = 'Username not found'
						return render_template('login.html', error=error)
			else:
				error = 'Username not found'
				return render_template('login.html', error=error)

	return render_template('login.html')




#Check if user is logged in
def is_logged_in(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'logged_in' in session:
			return f(*args, **kwargs)
		else:
			flash('Unauthorized, Please login', 'danger')
			return redirect(url_for('login'))
	return wrap

#Select the appropriate test file for the username provided
def select_database(dataBaseName):

	dataBaseName = dataBaseName
	try:
		os.path.isfile(dataBaseName)
		return dataBaseName

	except FileNotFoundError:
		flash('This is a new user. A new database has been created!', 'success')

	createTables(dataBaseName)



# set databaseName
def setDataBaseName(IncomingDataBaseName):
	global dataBaseName
	dataBaseName = IncomingDataBaseName



# get databaseName
def getDataBaseName():
	global dataBaseNames
	return dataBaseName

# create database createTables
def createTables(dataBaseName):
	with sql.connect(dataBaseName) as connection:

		cur = connection.cursor()

		# users
		cur.execute("CREATE TABLE IF NOT EXISTS users (userId INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,username varchar(30) DEFAULT NULL,password varchar(100) DEFAULT NULL,register_date timestamp NOT NULL DEFAULT (datetime('now','localtime')))")
		# members
		cur.execute("CREATE TABLE IF NOT EXISTS members (clientId INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, name varchar(50) NOT NULL,totalBreakfast int(11) DEFAULT 10, leftTillFree int(11) DEFAULT 10, author varchar(50) DEFAULT NULL, creationDate timestamp NOT NULL DEFAULT (datetime('now','localtime')))")
		# visits
		cur.execute("CREATE TABLE IF NOT EXISTS visits (visitId INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,clientId int(11) DEFAULT NULL,breakfastDate timestamp NOT NULL DEFAULT (datetime('now','localtime')),author varchar(50) DEFAULT NULL, FOREIGN KEY(clientId) REFERENCES members(clientId))")
		# redeem
		cur.execute("CREATE TABLE IF NOT EXISTS redeem (redeemId INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,clientId int(11) DEFAULT NULL,redeemDate timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,author varchar(50) DEFAULT NULL,redeem tinyint(1) NOT NULL DEFAULT '0', FOREIGN KEY(clientId) REFERENCES members(clientId))")

		return dataBaseName

#Logout
@app.route('/logout/')
@is_logged_in
def logout():
	session.clear
	flash('You are now logged out', 'success')
	session['logged_in'] = False
	return redirect(url_for('login'))



#memberSearch (Dashboard)
@app.route('/memberSearch/', defaults={'defSess': None})
@app.route('/memberSearch/<defSess>')
@is_logged_in
def memberSearch(defSess):

	if defSess is None:
		session.clear()
		flash('Unauthorized, Please login', 'danger')
		return render_template('login.html')
	else:
		defSess = defSess

		createTables(defSess)

		with sql.connect(defSess) as connection:
			connection.row_factory = sql.Row

			cur = connection.execute("SELECT * from members m join visits v where v.breakfastDate = (select max(visits.breakfastDate) from visits where visits.clientId = m.clientId) UNION select * from members m left join visits v on m.clientId = v.clientId where breakfastDate is NULL")

			members = build_dict_list(cur)
			if members:
				return render_template('memberSearch.html', members=members,defSess=defSess)
			else:
				msg = 'No members Found'
				return render_template('memberSearch.html', msg=msg, defSess=defSess)



# Utility Functions
def build_dict_list(cur):
	dict_list = []

	nextElement = cur.fetchone()
	while nextElement is not None:
		dict_list.append(nextElement)
		nextElement = cur.fetchone()

	return dict_list

#Member Form class
class MemberForm(Form):
	name = StringField('Name', [validators.Length(min=1, max=50)])

#visitSearch (Dashboard)
@app.route('/visitSearch/<string:id>/<defSess>', methods=['GET', 'POST'])
@is_logged_in
def visitSearch(id, defSess):
	defSess = defSess
	with sql.connect(defSess) as connection:
		connection.row_factory = sql.Row

		cur = connection.execute("SELECT * FROM visits WHERE clientId = ?", [id])

		result = cur.execute("SELECT * from members, visits WHERE members.clientId = ? AND visits.clientId = members.clientId", [id])
		visits = build_dict_list(cur)

		if visits:
			return render_template('visitSearch.html', visits=visits, name=visits[0]['name'], defSess=defSess)
		else:
			msg = 'No visits Found'
			return render_template('visitSearch.html', msg=msg, defSess=defSess)


# Add Visit
@app.route('/add_visit/<string:id>/<defSess>', methods=['GET', 'POST'])
@is_logged_in
def add_visit(id, defSess):
	defSess=defSess
	if request.method == 'POST':

		with sql.connect(defSess) as connection:
			# Create Cursor
			cur = connection.cursor()
			author = session['username']

			addVisitButton = True


			# Execute
			cur.execute("INSERT INTO visits(clientId, author) VALUES(?,?)", [id,author])

			person = cur.execute("SELECT * FROM visits WHERE clientId = ?", [id])

			cur.execute("UPDATE members SET totalBreakfast = (SELECT count(*) FROM visits WHERE clientId = ?) WHERE clientId = ?", [id, id])

			leftTillFree = addVisitLeftTillFree(id, defSess)

			cur.execute("UPDATE members SET leftTillFree = ? WHERE clientId = ?", [leftTillFree, id])

			flash('Visit created for ', 'success')


		return redirect(url_for('memberSearch', defSess=defSess))


def addVisitLeftTillFree(id, defSess):

	with sql.connect(defSess) as connection:

		cur = connection.cursor()

		cur.execute("SELECT * FROM members WHERE clientId = ?", [id])
        result = cur.execute("SELECT * FROM members WHERE clientId = ?", [id])
        result = cur.fetchone()
        numVisits = result[2]
        leftTillFree = 9-numVisits%10

	return leftTillFree



# Add member
@app.route('/add_member/<defSess>/', methods=['GET', 'POST'])
@is_logged_in
def add_member(defSess):
    form = MemberForm(request.form)

    if request.method == 'POST' and form.validate():
        with sql.connect(defSess) as connection:
            name = form.name.data
            author = defSess
            connection.execute("INSERT INTO members(name, author) VALUES(?,?)",[name,author],)
            flash('Member Created', 'success')

            return redirect(url_for('memberSearch', defSess=defSess))

    return render_template('add_member.html', form=form, defSess=defSess)


# Delete Visit
@app.route('/delete_visit/<string:visitId>/<string:clientId>/<defSess>', methods=['POST'])
@is_logged_in
def delete_visit(visitId,clientId, defSess):
	defSess=defSess
	with sql.connect(defSess) as connection:

		cur = connection.cursor()

		visitId = [visitId]

		# Execute Delete
		cur.execute("DELETE FROM visits WHERE visitId = ?", (visitId),)

		leftTillFree = removeVisitLeftTillFree(clientId, defSess)

		cur.execute("UPDATE members SET leftTillFree = ? WHERE clientId = ?", [leftTillFree, clientId])

		cur.execute("UPDATE members SET totalBreakfast = (SELECT count(*) FROM visits WHERE clientId = ?) WHERE clientId = ?", [clientId,clientId])

	return redirect(url_for('visitSearch', id=clientId, defSess=defSess))




def removeVisitLeftTillFree(id, defSess):

	with sql.connect(defSess) as connection:

		cur = connection.cursor()

		cur.execute("SELECT * FROM members WHERE clientId = ?", [id])

		result = cur.fetchone()
		numVisits = result[3]

		leftTillFree = numVisits+1

	return leftTillFree

#Delete a member
@app.route('/delete_member/<string:id>/<defSess>', methods=['POST'])
@is_logged_in
def delete_member(id, defSess):
	defSess=defSess
	addVisitButton=addVisitButton

	with sql.connect(defSess) as connection:
		# Create cursor
		cur = connection.cursor()

		# Deletes member

		cur.execute("DELETE FROM members WHERE clientId = ?", [id])

		#deletes visits associated with member
		cur.execute("DELETE FROM visits WHERE clientId = ?", [id])

		flash('Member Deleted', 'success')

		return redirect(url_for('memberSearch', defSess=defSess))

if __name__ == '__main__':
	app.run(debug=True)
