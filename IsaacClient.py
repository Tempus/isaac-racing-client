import sys, os, random, json
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebSockets import *
from PyQt5.QtNetwork import *

# Server Command Quick Reference
# 
# Outgoing
# 	roomJoin {"name":"fartchannel"}
# 	roomMessage {"to":"global","msg":"i poopd"}
# 	privateMessage {"to":"zamiel","msg":"private message lol"} 
# 	raceCreate {}
# 	raceJoin {"number":5}
# 	raceLeave {"number":5}
# 	raceReady {"number":5}
# 	raceUnready {"number":5}
# 	logout {}
# 
# Incoming
#	SuccessMessage {"type", "msg"}
#	ErrorMessage {"type", "msg"}
#	RoomMessage (roomJoin, roomLeave) {"name"}
#	ChatMessage {"to", "from", "msg"}
#	RoomList {"room", "users"}
#	User {"name", "admin"}
#	RaceList {"races"}
#	Race {"id", "status", "ruleset", "datetime_created", "datetime_started", "created_by"}
#	RaceMessage {"number"}
#	RaceParticipantList {"race_id", "racers"}
#	Racer {"name", "status", "admin"}
#


# Contains all the network connection data
class Connection():

	HOST = QUrl("wss://isaacitemtracker.com/ws")

	REGISTER = "https://isaacserver.auth0.com/dbconnections/signup"
	AUTH_LOGIN = "https://isaacserver.auth0.com/oauth/ro"
	HOST_LOGIN = "https://isaacitemtracker.com/login"

	CLIENT = "tqY8tYlobY4hc16ph5B61dpMJ1YzDaAR"

	# Setup the connection and the signals
	def __init__(self):
		self.connection = QWebSocket()
		
		self.connection.connected.connect(self.connected)
		self.connection.disconnected.connect(self.disconnected)
		self.connection.error.connect(self.error)

		self.http = QNetworkAccessManager()
		self.http.finished.connect(self.reply)
		self.httpWait = None

		# QNetworkReply()
		# parse cookie
		# QNetworkCookie()

		self.cookie = QNetworkCookie()

	
	# Waits for network reply
	def reply(self, httpReply):

		if httpReply.error() == 0:
			if self.httpWait:
				self.httpWait(httpReply)
		else:
			print ("Error: {0}".format(httpReply.error()))

	# Authorization
	def register(self, username, password):
		# // curl https://isaacserver.auth0.com/dbconnections/signup -H "Content-Type: application/json" --data '{"client_id":"tqY8tYlobY4hc16ph5B61dpMJ1YzDaAR","email":"zamiel@zamiel3.com","username":"zamiel","password":"asdf","connection":"Username-Password-Authentication"}' --verbose
		pass

	# Begins the login sequence with the authorization
	def login(self, username, password):
		# Set where the next step in the chain leads
		self.httpWait = self.loginCallback

		# Generate the body data
		body = QByteArray().append("grant_type=password&username={0}&password={1}&client_id={2}&connection=Username-Password-Authentication".format(username, password, self.CLIENT))

		# Make the request to the URL with the appropriate header
		request = QNetworkRequest(QUrl(self.AUTH_LOGIN))
		request.setHeader(QNetworkRequest.ContentTypeHeader, QVariant("application/x-www-form-urlencoded"))

		# Up up and away
		reply = self.http.post(request, body)

	# The login callback following the auth
	def loginCallback(self, httpReply):

		# Set where the next step in the chain leads
		self.httpWait = self.loginSuccessConnect

		# Generate the body data
		replyData = str(httpReply.read(10000000), 'utf-8')
		body = QByteArray().append(replyData)

		# Make the request to the URL with the appropriate header
		request = QNetworkRequest(QUrl(self.HOST_LOGIN))
		request.setHeader(QNetworkRequest.ContentTypeHeader, QVariant("application/json"))

		# Send the request
		reply = self.http.post(request, QByteArray().append(replyData))

	# Occurs on login success
	def loginSuccessConnect(self, httpReply):
		request = QNetworkRequest(QUrl(self.HOST))
		# request.setRawHeader(QByteArray(), httpReply.rawHeader(httpReply.rawHeaderList()[0]))

		cookie = httpReply.header(QNetworkRequest.SetCookieHeader)
		request.setHeader(QNetworkRequest.SetCookieHeader, cookie)

		self.connection.open(request)

	# Writes data to the server connection
	def sendData(self, msg):
		self.connection.sendTextMessage(msg)
		print("Send Msg: {}".format(msg))

	def connected(self):
		print("Connected")

	# Fallback if the server dies
	def disconnected(self):
		print("Disconnected")
		self.connection.close()
 
	def error(self):
		print(self.connection.errorString())


# Represents the Screen players login
class LoginScreen(QWidget):

	def __init__(self):
		QWidget.__init__(self)

		# Widgets
		usernameField = QLineEdit()
		passwordField = QLineEdit()

		submit = QPushButton("Submit")
		cancel = QPushButton("Cancel")

		submit.released.connect(self.login)
		cancel.released.connect(quit)

		# Layout
		self.loginForm = QFormLayout()
		self.loginForm.addRow("Username", usernameField)
		self.loginForm.addRow("Password", passwordField)
		self.loginForm.addRow(submit, cancel)

		self.setLayout(self.loginForm)

		net.login("zamiel", "asdf")

	def login(self):
		mainWindow.setCentralWidget(Lobby())

# Represents the Lobby to join ongoing races
class Lobby(QWidget):

	def __init__(self):
		QWidget.__init__(self)

		# Widget Setup
		raceList = QListWidget()
		chat = QListWidget()
		chatEntry = QLineEdit()
		userList = QListWidget()

		logoutButton = QPushButton("Logout")
		logoutButton.released.connect(self.logout)

		# Layouts Setup
		chatLayout = QVBoxLayout()
		chatLayout.addWidget(chat)
		chatLayout.addWidget(chatEntry)

		userLayout = QVBoxLayout()
		userLayout.addWidget(userList)
		userLayout.addWidget(logoutButton)
		userLayout.setSpacing(0)

		bottomLayout = QGridLayout()
		bottomLayout.addLayout(chatLayout, 0, 0)
		bottomLayout.addLayout(userLayout, 0, 1)
		bottomLayout.setColumnStretch(0, 1)

		layout = QVBoxLayout()
		layout.addWidget(raceList)
		layout.addLayout(bottomLayout)

		self.setLayout(layout)

	def logout(self):
		mainWindow.setCentralWidget(LoginScreen())


# Represents the Game ruleset and pregame area
class StagingArea(QWidget):

	def __init__(self):
		QWidget.__init__(self)

		# Widget Setup
		chat = QListWidget()
		chatEntry = QLineEdit()
		userList = QListWidget()

		self.readyButton = QPushButton("Ready")
		self.readyButton.released.connect(self.toggleReady)

		self.startButton = QPushButton("Start Race")
		self.startButton.released.connect(self.startRace)
		self.startButton.setEnabled(False)

		leaveButton = QPushButton("Leave Race")
		leaveButton.released.connect(self.leaveRace)

		# Layout Setup
		chatLayout = QVBoxLayout()
		chatLayout.addWidget(chat)
		chatLayout.addWidget(chatEntry)

		userLayout = QVBoxLayout()
		userLayout.addWidget(self.startButton)
		userLayout.addWidget(self.readyButton)
		userLayout.addWidget(userList)
		userLayout.addWidget(leaveButton)
		# userLayout.setSpacing(0)

		layout = QHBoxLayout()
		layout.addLayout(chatLayout)
		layout.addLayout(userLayout)
	
		self.setLayout(layout)

	def toggleReady(self):
		if self.readyButton.text() == "Ready":
			self.readyButton.setText("Unready")
			self.startButton.setEnabled(True)
		else:
			self.readyButton.setText("Ready")
			self.startButton.setEnabled(False)


	def startRace(self):
		mainWindow.setCentralWidget(IsaacScene())

	def leaveRace(self):
		mainWindow.setCentralWidget(Lobby())


# Represents the Isaac Game
class IsaacScene(QGraphicsView):

	def __init__(self):
		QGraphicsView.__init__(self, QGraphicsScene())

		# Basic Setup
		s = self.scene()
		self.setSceneRect(0,0,800,450)
		s.setBackgroundBrush(QColor(0, 100, 255, 20))

		# Timer
		self.startTime = QDateTime.currentDateTime()
		self.timerText = s.addText("00:00:00:00")
		self.timerText.setPos(352,12)
		self.startTimer(0)

		# Messsages to send

		# Floor messages
		floorButton = QPushButton("Next Floor")
		floorButton.released.connect(self.newFloor)
		w = s.addWidget(floorButton)

		self.floors = ["B1", "B2", "C1", "C2", "D1", "D2", "W1", "W2", "Cath", "Chest"]
		self.floorIndex = 0

		# Item messages
		itemButton = QPushButton("Get Random Item")
		itemButton.released.connect(self.newItem)
		w = s.addWidget(itemButton)
		w.setY(24)


		# Recieving messages
		net.connection.textMessageReceived.connect(self.gotMessage)


	# Send a new floor message
	def newFloor(self):
		net.sendData('join {"name":"poop"}')

		# net.sendData('"{0}", "{1}"'.format(self.startTime.msecsTo(QDateTime.currentDateTime()), self.floors[self.floorIndex]))
		# self.floorIndex = self.floorIndex + 1
		# if self.floorIndex >= len(self.floors):
		# 	net.sendData('"{0}", "Run Complete"'.format(self.startTime.msecsTo(QDateTime.currentDateTime())))
		# 	app.quit()

	# Send a new item collection
	def newItem(self):
		net.sendData('msg { "to":"poop", "msg":"i farted" }')

		# net.sendData('"{0}", "{1}", "{2}"'.format(self.startTime.msecsTo(QDateTime.currentDateTime()), self.floors[self.floorIndex], random.randint(0,300)))

	# Timer Update
	def timerEvent(self, event):
		time = self.startTime.msecsTo(QDateTime.currentDateTime())

		h = int(time / 1000 / 60 / 60)
		m = int((time / 1000 / 60) - (h * 60))
		s = int((time / 1000) - ((m + (h * 60))* 60))
		ms = time & 1000

		curTime = "{0:02}:{1:02}:{2:02}:{3:03}".format(h,m,s,ms)

		self.timerText.setPlainText(curTime)

	# Process received messages
	def gotMessage(self, msg):
		print("Received: {0}".format(msg))


# Main Window Class. Just used for containers
class MainWindow(QMainWindow):

	# Setup the window
	def __init__(self):
		QMainWindow.__init__(self)

		self.setWindowTitle('Isaac Client')
		self.setIconSize(QSize(16, 16))
		self.setGeometry(100, 500, 800, 450)

		self.setCentralWidget(LoginScreen())


if __name__ == '__main__':

	# Application
	app = QApplication(sys.argv)
	# app.setWindowIcon(QIcon('Icon.png'))

	net = Connection()
	mainWindow = MainWindow()
	mainWindow.show()

	sys.exit(app.exec_())
