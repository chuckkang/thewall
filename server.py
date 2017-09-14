from flask import Flask, render_template, request, redirect, session, flash
import random
from datetime import datetime 
from datetime import timedelta
import re
import md5 # imports the md5 module to generate a hash
import os, binascii # include this at the top of your file

from mysqlconnection import MySQLConnector

app = Flask(__name__)
app.secret_key = " this is the secret key"

# create a regular expression object that we can use run operations on
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$')
mysqldb = MySQLConnector(app, "thewall") # create the connection
# salt = binascii.b2a_hex(os.urandom(15)) #salt characters

	
@app.route('/', methods=['POST', 'GET'])
def index():

	isValid = False
	logindata = {'email': '', 'password':''}
	if request.method=="POST":
		email = request.form['email'].strip().lower()
		password = request.form['password'].strip()
		logindata = {'email': email, 'password': password}
		if (len(email)<1 or len(password)<1):
			flash("Please enter a username and password.")
		else:
			if (len(email)>0):
				
				salt_key = getSaltKey(email)
				if (salt_key==False):
					flash("No usernames by this email have been found")
				else:					
					password = md5.new(password+salt_key).hexdigest()
					dictResult = getLogin(email, password)
					if (len(dictResult)==0):
						flash("No usernames were found")
					else:
						setSessionVariables(dictResult)
						isValid = True
	else:
		clearSession()	
	if isValid == True:
		return redirect ('/wall/'+ str(session['userid']) + '')
	else:	
	 	return render_template("index.html", requestDict=logindata)

	


@app.route('/register', methods=['POST', 'GET'])
def register():
	isFormValid = False
	if (request.method=='GET'):
		#set up variables
		requestDict = {'first':'', 'last':'', 'email':'', 'dob':'', 'password':'', 'verifypass':''}
	elif (request.method=='POST'):
		first = request.form['first_name'].strip()
		last = request.form['last_name'].strip()
		email = request.form['email'].strip().lower()
		dob = request.form['dob'].strip()
		password = request.form['password'].strip()
		verifypass = request.form['verifypass'].strip()
		requestDict = {'first':first, 'last':last, 'email':email, 'dob':dob, 'password':password, 'verifypass':verifypass}
		
		# for key in requestDict:
		# 	print (key, "--post")

		if isNameValid('first', first)==True:
			if isNameValid('last', last)==True:
				if isEmailValid(email)==True:
					if isDateValid(dob)==True:
						if isPasswordValid("password", password, verifypass)==True:
							if isPasswordValid("verifypass", password, verifypass)==True:
								if doesEmailExist(email)==False:
								#insert datainto the database
									salt = binascii.b2a_hex(os.urandom(15))
									password = md5.new(password + salt).hexdigest()
									data = {'first_name': first, 'last_name': last, 'email': email, 'dob':dob, 'password': password, 'salt': salt}
									userid = insertNewAccount(data)
									useridkey = {'id': userid}
									dctUserInfo = getUserInfo(useridkey)
									if dctUserInfo!=0:
										setSessionVariables(dctUserInfo)

									isFormValid=True
								else:
									flash("There is already an account with this email address.")
								
  	if isFormValid==True:
		return redirect("/confirmation/" + str(session['userid']))
	else:
		return render_template("register.html", requestDict=requestDict)



@app.route('/wall/<userid>', methods=['GET'])
def wall(userid):
	checkSession(session['login'])

	sql = "SELECT users.id as user_id, CONCAT_WS(' ', users.first_name, users.last_name) AS full_name, messages.id as message_id, messages.message, messages.created_at as message_created FROM users JOIN messages ON users.id = messages.user_id ORDER BY message_created"
	msgData = {}
	dctMessages = mysqldb.query_db(sql, msgData)

	sqlComment = 'SELECT comments.id, comments.user_id, comments.comment, comments.created_at, comments.message_id, CONCAT_WS(" ", users.first_name, users.last_name) as comment_username FROM users JOIN comments ON comments.user_id = users.id ORDER BY comments.created_at'
	msgData = {}
	dctComments = mysqldb.query_db(sqlComment, msgData)
	# print dctComments
	return render_template('wall.html', messagedata=dctMessages, commentsdata=dctComments)

@app.route('/postmessage/<userid>', methods=['POST'])
def post_message(userid):
	if checkSession(session['login'])!=True:
		return redirect ("/")

	message = request.form['message'].strip()
	if isInputEmpty("message", message)==False:
		sql = "INSERT INTO messages(message, user_id) values (:message, :id)"
		msgData = {'message': message, 'id': session['userid']}
		intKey = mysqldb.query_db(sql, msgData)
		
	page = '/wall/'+str(session['userid'])
	return redirect(page)

@app.route('/postcomment/<message_id>', methods=['POST'])
def post_comment(message_id):
	if checkSession(session['login'])!=True:
		return redirect ("/")
	comment = request.form['comment'].strip()
	
	if isInputEmpty("comment", comment)==False:
		sql = "INSERT INTO comments(comment, message_id, user_id) values (:comment, :message_id, :id)"
		msgData = {'comment': comment,'message_id': message_id, 'id': session['userid']}
		intKey = mysqldb.query_db(sql, msgData)
		
	page = '/wall/'+str(session['userid'])
	return redirect(page)




@app.route('/confirmation/<userid>', methods=['GET'])
def confirmation(userid):
	if checkSession(session['login'])!=True:
		return redirect ("/")
	return render_template('confirmation.html', id = userid)








@app.route('/logout', methods=['GET'])
def logout():
	for i in session:
		i = None
	return redirect('/')
##################################Application functions####################################################
def isInputEmpty(input_name, form_input):
	isEmpty = True
	if (form_input.strip()==''):
		errMessage = "Please enter a " + input_name + "."
		flash(errMessage)
	else:
		isEmpty = False

	return isEmpty
def doesEmailExist(email):
	sql = "SELECT users.email from users WHERE email = :email LIMIT 1"
	email = email.lower()
	emaildata = {'email': email}
	dctEmail = mysqldb.query_db(sql, emaildata)

	if len(dctEmail)==0:
		return False
	else:
		return True

def getSaltKey(email):
	sql = "SELECT users.salt FROM users WHERE email = :email"
	email = email.lower()
	emaildata = {'email': email}
	dct = mysqldb.query_db(sql, emaildata)
	if len(dct)>0:
		return dct[0]['salt']
	else:
		return False

def getUserInfo(data):
	newdata = data
	sql = "SELECT * FROM users WHERE users.id = :id LIMIT 1"
	userData = mysqldb.query_db(sql, newdata)
	# print userData, "THISis the userdata"
	return userData
def getLogin(email, password):
	sql = "SELECT users.id, users.first_name, users.last_name, users.email, users.password from users where email= :email AND password= :password LIMIT 1"
	data = {'email': email, 'password': password}
	dictResult = mysqldb.query_db(sql, data)
	return dictResult

def setSessionVariables(dictUser):
	session['userinfo'] = dictUser
	session['userid'] = session['userinfo'][0]['id']
	session['first_name'] = session['userinfo'][0]['first_name']
	session['last_name'] = session['userinfo'][0]['last_name']
	session['email'] = session['userinfo'][0]['email']
	session['login']=True
	return True

def checkSession(login):
	if session['login'] == True:
		return True
	else:
		clearSession()
		return redirect ("/")

def clearSession():
	session.clear()
	return True

def isEmailValid(email):
	if EMAIL_REGEX.match(email):
		return True
	else:
		flash("Email is not in the correct format.  Please re-enter your email.")
		return False
	return True



def insertNewAccount(data):
	sql = "INSERT INTO users(first_name, last_name, email, dob, password, salt) VALUES(:first_name, :last_name, :email, :dob, :password, :salt)"
	insert = mysqldb.query_db(sql, data)
	return insert



def isPasswordValid(passtype, val1, val2):
	# this function will return an empty string if the password is not valid
	msg = ''
	isValid = False
	if passtype == 'password' :
		msgType = 'Password'
	elif passtype == 'verifypass':
		msgType = 'Verification Password'
	# print passtype, (val1==val2), "ASDFASDF	"
	if passtype == "password":	
		if (len(val1) < 8 or (len(val1) > 20)):
			flash(msgType + " must be longer than eight characters and less than 20", "password")
			# print "it loaded the flash"
		elif (CheckUpperCase(val1)!=True):
			flash(msgType + " must be contain at least one capital letter and one number", "password")
		elif (CheckNumeric(val1)!=True):
			flash(msgType + " must be contain at least one number", "password")
		else:
			isValid = True
	elif passtype == "verifypass":
		if (val1!=val2):
			flash("Passwords do not match.  Please re-enter your passwords", "veriypass")
			# print val1!=val2, "-verifypass"
			
		else:
			isValid = True
	# print "passwordvalid", isValid
	return isValid
		
def isNameValid(firstLast, val):
	isValid = False
	msg = ''
	msgName = ''
	if (firstLast=='first'):
		msgName = 'first'
	elif (firstLast == 'last'):
		msgName = 'last'
	
	if (len(val) < 1 ):
		flash(('Please enter your {} name'.format(msgName)), "{}name".format(msgName))
	elif (len(val) > 10):
		flash(('Please enter less than {} characters'.format("10")), "{}name".format(msgName))
	elif val.isalpha()==False:
		flash(('Your {} name must not include any numbers, spaces, or special characters(!@#$%^&*()~:;<>?).'.format(msgName)), "{}name".format(msgName))
	else:
		isValid = True
	return isValid

def isDateValid(val):
	isValid = False
	# print datetime.strptime('1974-10-18', '%Y-%m-%d')
	try:
		if datetime.strptime(val, '%Y-%m-%d'):
			isValid = True
			# print val, " date  parse"
	except ValueError:
		isValid = False
		# print timedelta(years=60)  
		print val, " date didn't parse"
		flash("The birthday must be in correct format. dd-mm-yyyy")
	# print isValid, "is date valid"
	return isValid

def CheckUpperCase(val):
	isValid = False
	for i in range(0, len(val)):
		if val[i].isupper():
			# print val[i], "upper case is true"
			return True
	return isValid

def CheckNumeric(val):
	isValid = False
	for i in val:
		if i.isdigit():
			isValid = True
			# print i, "--is digit"
			return True
	return isValid
	
	
app.run(debug=True) # run our server