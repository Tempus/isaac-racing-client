import sys, os, random, json
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebSockets import *
from PyQt5.QtNetwork import *

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
	
	# Waits for network reply
	def reply(self, httpReply):

		if httpReply.error() == 0:
			if self.httpWait:
				self.httpWait(httpReply)
		else:
			print ("Error: {0}".format(httpReply.error()))

	# Authorization
	def register(self, username, password, email):
		self.httpWait = self.login
		self.username = username
		self.password = password

		# Generate the body data
		body = QByteArray().append('{{"client_id":"{0}","email":"{3}","username":"{1}","password":"{2}","connection":"Username-Password-Authentication"}}'.format(self.CLIENT, username, password, email))
 
		# Make the request to the URL with the appropriate header
		request = QNetworkRequest(QUrl(self.REGISTER))
		request.setHeader(QNetworkRequest.ContentTypeHeader, QVariant("application/json"))

		# Send in the registration
		self.http.post(request, body)

	# Begins the login sequence with the authorization
	def login(self, username = None, password = None):
		if username == None:
			username = self.username
		if password == None:
			password = self.password

		# Set where the next step in the chain leads
		self.httpWait = self.loginCallback

		# Generate the body data
		body = QByteArray().append("grant_type=password&username={0}&password={1}&client_id={2}&connection=Username-Password-Authentication".format(username, password, self.CLIENT))

		# Make the request to the URL with the appropriate header
		request = QNetworkRequest(QUrl(self.AUTH_LOGIN))
		request.setHeader(QNetworkRequest.ContentTypeHeader, QVariant("application/x-www-form-urlencoded"))

		# Up up and away
		self.http.post(request, body)

	# The login callback following the auth
	def loginCallback(self, httpReply):

		# Set where the next step in the chain leads
		self.httpWait = self.loginSuccessConnect

		# Generate the body data
		body = QByteArray().append(str(httpReply.read(10000000), 'utf-8'))

		# Make the request to the URL with the appropriate header
		request = QNetworkRequest(QUrl(self.HOST_LOGIN))
		request.setHeader(QNetworkRequest.ContentTypeHeader, QVariant("application/json"))

		# Send the request
		self.http.post(request, body)

	# Occurs on login success
	def loginSuccessConnect(self, httpReply):
		request = QNetworkRequest(QUrl(self.HOST))

		cookie = httpReply.header(QNetworkRequest.SetCookieHeader)
		request.setHeader(QNetworkRequest.CookieHeader, cookie[0])

		self.connection.open(request)

	# Writes data to the server connection
	def sendData(self, msg):
		self.connection.sendTextMessage(msg)
		print("Send Msg: {}".format(msg))

	# Occurs on successful connection
	def connected(self):
		print("Connected")
		return

	# Fallback if the server dies
	def disconnected(self):
		print("Disconnected")
		self.connection.close()
		mainWindow.setCentralWidget(LoginScreen())

 
	# Called on a connection error
	def error(self):
		print(self.connection.errorString())
		return


class ServerConnection(QObject):

	# Singals for all the messages we expect to receive
	RoomList 	= pyqtSignal(str, list) 	# {"room", "users"}
	RaceList 	= pyqtSignal(list) 			# {"races"}
	Success 	= pyqtSignal(str, str)		# {"type", "msg"}
	RoomMessage = pyqtSignal(str, str, str)	# {"to", "from", msg"}

	def __init__(self):
		QObject.__init__(self)

		self.connected = False
		net.connection.textMessageReceived.connect(self.parseMessage)

	####################
	# Outgoing Commands
	####################

	def roomJoin(self, name):
		net.sendData('roomJoin {{"name":"{0}"}}'.format(name))

	def roomMessage(self, to, msg):
		net.sendData('roomMessage {{"to":"{0}", "msg":"{1}"}}'.format(to, msg))

	def privateMessage(self, to, msg):
		net.sendData('privateMessage {{"to":"{0}", "msg":"{1}"}}'.format(to, msg))

	def raceCreate(self):
		net.sendData('raceCreate {}')

	def raceJoin(self, id):
		net.sendData('roomJoin {{"id":"{0}"}}'.format(id))

	def raceLeave(self, id):
		net.sendData('raceLeave {{"id":"{0}"}}'.format(id))

	def raceReady(self, id):
		net.sendData('raceReady {{"id":"{0}"}}'.format(id))

	def raceUnready(self, id):
		net.sendData('raceUnready {{"id":"{0}"}}'.format(id))

	def raceDone(self, id):
		net.sendData('raceDone {{"id":"{0}"}}'.format(id))

	def raceQuit(self, id):
		net.sendData('raceQuit {{"id":"{0}"}}'.format(id))

	def raceFloor(self, floor, id):
		net.sendData('raceFloor {{"id":"{0}", "floor":"{0}"}}'.format(id, floor))

	def logout(self):
		net.sendData('logout {}')

	def banUser(self, username):
		net.sendData('adminBan {{"name":"{0}"}}'.format(username))

	def squelchUser(self, username):
		net.sendData('adminSquelch {{"name":"{0}"}}'.format(username))

	####################
	# Incoming Commands
	####################

	def parseMessage(self, message):
		try:
			command = message.split(" ", 1)
			body = json.loads(command[1])

			if command[0] == "roomList":
				self.RoomList.emit(body["room"], body["users"])

			elif command[0] == "raceList":
				self.RaceList.emit(body["races"])

			elif command[0] == "success":
				self.Success.emit(body["type"], body["msg"])

			elif command[0] == "roomMessage":
				self.RoomMessage.emit(body["to"], body["from"], body["msg"])

			else:
				print ("Unknown Command: '{0}'".format(message))

			print ("Recv Msg: {0}".format(message))

		except:
		 	print ("Bad Command format: '{0}'".format(message))


# Represents the Screen players login
class LoginScreen(QWidget):

	def __init__(self):
		QWidget.__init__(self)

		# Widgets
		self.usernameField = QLineEdit()
		self.passwordField = QLineEdit()

		self.rusernameField = QLineEdit()
		self.rpasswordField = QLineEdit()
		self.remailField = QLineEdit()

		submit = QPushButton("Submit")
		cancel = QPushButton("Quit")
		register = QPushButton("Register")

		submit.released.connect(self.login)
		cancel.released.connect(self.quit)
		register.released.connect(self.register)

		# Layout
		self.loginForm = QFormLayout()
		self.loginForm.addRow(QLabel(""), QLabel("Login"))
		self.loginForm.addRow("Username", self.usernameField)
		self.loginForm.addRow("Password", self.passwordField)
		self.loginForm.addRow(QLabel(""), submit)
		self.loginForm.addRow(QLabel(""), QLabel(""))

		self.loginForm.addRow(QLabel(""), QLabel("Register"))
		self.loginForm.addRow("Username", self.rusernameField)
		self.loginForm.addRow("Password", self.rpasswordField)
		self.loginForm.addRow("Email", self.remailField)
		self.loginForm.addRow(QLabel(""), register)
		self.loginForm.addRow(QLabel(""), QLabel(""))

		self.loginForm.addRow(QLabel(""), cancel)

		self.setLayout(self.loginForm)

		# Testing Shit
		# net.login("Chronometrics", "test")
		# net.connection.connected.connect(self.loginComplete)

	def login(self):
		net.connection.connected.connect(self.loginComplete)
		net.login(self.usernameField.text(), self.passwordField.text())

	def register(self):
		net.register(self.rusernameField.text(), self.rpasswordField.text(), self.remailField.text())

	def loginComplete(self):
		server.roomJoin("global")
		mainWindow.setCentralWidget(Lobby())

	def quit(self):
		mainWindow.quit()

# Represents the Lobby to join ongoing races
class Lobby(QWidget):

	def __init__(self):
		QWidget.__init__(self)

		self.tabs = QTabWidget()

		self.tabs.setTabShape(QTabWidget.Triangular)
		self.tabs.setTabsClosable(True)
		self.tabs.setMovable(True)

		self.tabs.addTab(RoomTab("global"), "global")

		logout = QPushButton("Logout")
		joinRoom = QPushButton("Join Room")
		newRace = QPushButton("New Race")

		logout.released.connect(self.logout)
		joinRoom.released.connect(self.joinRoom)
		newRace.released.connect(self.newRace)

		buttons = QHBoxLayout()
		buttons.addWidget(newRace)
		buttons.addWidget(joinRoom)
		buttons.addWidget(logout)

		layout = QVBoxLayout()
		layout.addWidget(self.tabs)
		layout.addLayout(buttons)

		self.setLayout(layout)

	def logout(self):
		server.logout()
		mainWindow.setCentralWidget(LoginScreen())

	def newRace(self):
		dialog = QInputDialog()
		raceName, completed = dialog.getText(self, "New Race", "Choose a name for your race.")

		if completed:
			server.raceCreate()
			self.tabs.addTab(RoomTab(raceName), raceName)

	def joinRoom(self):
		dialog = QInputDialog()
		roomName, completed = dialog.getText(self, "Join Room", "Enter the name of the room to join.")

		if completed:
			server.roomJoin(roomName)
			self.tabs.addTab(RoomTab(roomName), roomName)


# A Room or Race tab
class RoomTab(QWidget):

	def __init__(self, name):
		QWidget.__init__(self)
		self.name = name

		# Widget Setup
		self.raceList = QListWidget()
		self.chat = QListWidget()
		self.chatEntry = QLineEdit()
		self.userList = QListWidget()

		self.chatEntry.returnPressed.connect(self.sendMessage)

		# Layouts Setup
		chatLayout = QVBoxLayout()
		chatLayout.addWidget(self.chat)
		chatLayout.addWidget(self.chatEntry)

		userLayout = QVBoxLayout()
		userLayout.addWidget(self.userList)
		userLayout.setSpacing(0)

		bottomLayout = QGridLayout()
		bottomLayout.addLayout(chatLayout, 0, 0)
		bottomLayout.addLayout(userLayout, 0, 1)
		bottomLayout.setColumnStretch(0, 1)

		layout = QVBoxLayout()
		layout.addWidget(self.raceList)
		layout.addLayout(bottomLayout)

		self.setLayout(layout)

		# Server Signal setup
		server.RoomList.connect(self.updateUserlist)
		server.RaceList.connect(self.updateRacelist)
		server.RoomMessage.connect(self.updateChat)

	def updateUserlist(self, room, users):
		if room != self.name: return

		self.userList.clear()

		for user in users:
			self.userList.addItem(user["name"])

		self.userList.sortItems()

	def updateRacelist(self, races):
		self.raceList.clear()

		for race in races:
			self.raceList.addItem("Race {0}".format(race["id"]))

		self.raceList.sortItems()

	def updateChat(self, to, afrom, msg):
		if to != self.name: return

		self.chat.addItem("{0}: {1}".format(afrom, msg))

	def sendMessage(self):
		server.roomMessage(self.name, self.chatEntry.text())
		self.chatEntry.clear()

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

	# Quit the application cleanly
	def closeEvent(self, event):
		self.quit()

	def quit(self):
		server.logout()
		app.quit()


if __name__ == '__main__':

	# Application
	app = QApplication(sys.argv)
	# app.setWindowIcon(QIcon('Icon.png'))

	net = Connection()
	server = ServerConnection()
	mainWindow = MainWindow()
	mainWindow.show()

	sys.exit(app.exec_())
