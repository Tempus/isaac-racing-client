import sys, os, random, json, re, platform
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebSockets import *
from PyQt5.QtNetwork import *

#########################################################
#
#	Isaac Racing Client by Colin Noga
#	 All Rights Reserved
#
#
#	TODO:
#
#		Receiving Race Updates
#		Integration with Diversity, Jud6s, Instant Start
#		Ruleset Selection
#		Ruleset Validation
#		Countdown to the start
#		Banning, Squelching
#		Admin Rights
#		Updating with Zamiel's API changes
#		Adding Race features to the racing screen
#		Results Screen
#		Adjust Isaac Race to better suit watching player
#		Leaderboards
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


# Handles the server and client communications and API
class ServerConnection(QObject):

	# Singals for all the messages we expect to receive
	RoomList 	= pyqtSignal(str, list) 	# {"room", "users"}
	RaceList 	= pyqtSignal(list) 			# {"races"}
	RacerList 	= pyqtSignal(int, list) 	# {"id", "racers"}
	Success 	= pyqtSignal(str, dict)		# {"type", "msg"}
	Error 		= pyqtSignal(str, str)		# {"type", "msg"}
	RoomMessage = pyqtSignal(str, str, str)	# {"to", "from", msg"}
	RaceServer	= pyqtSignal(int, str)		# {"id", "msg"}

	def __init__(self):
		QObject.__init__(self)

		self.connected = False
		net.connection.textMessageReceived.connect(self.parseMessage)

	####################
	# Outgoing Commands
	####################

	def roomJoin(self, name):
		net.sendData('roomJoin {{"name":"{0}"}}'.format(name))

	def roomLeave(self, name):
		net.sendData('roomLeave {{"name":"{0}"}}'.format(name))

	def roomMessage(self, to, msg):
		net.sendData('roomMessage {{"to":"{0}", "msg":"{1}"}}'.format(to, msg))

	def privateMessage(self, to, msg):
		net.sendData('privateMessage {{"to":"{0}", "msg":"{1}"}}'.format(to, msg))

	def raceCreate(self, name):
		net.sendData('raceCreate {{"name":"{0}"}}'.format(name))

	def raceJoin(self, id):
		net.sendData('raceJoin {{"id":{0}}}'.format(id))

	def raceLeave(self, id):
		net.sendData('raceLeave {{"id":{0}}}'.format(id))

	def raceReady(self, id):
		net.sendData('raceReady {{"id":{0}}}'.format(id))

	def raceUnready(self, id):
		net.sendData('raceUnready {{"id":{0}}}'.format(id))

	def raceDone(self, id):
		net.sendData('raceDone {{"id":{0}}}'.format(id))

	def raceQuit(self, id):
		net.sendData('raceQuit {{"id":{0}}}'.format(id))

	def raceFloor(self, floor, id):
		net.sendData('raceFloor {{"id":{0}, "floor":"{0}"}}'.format(id, floor))

	def logout(self):
		net.sendData('logout {}')

	def banUser(self, username):
		net.sendData('adminBan {{"name":"{0}"}}'.format(username))

	def squelchUser(self, username):
		net.sendData('adminSquelch {{"name":"{0}"}}'.format(username))

	####################
	# Outgoing Commands (Race Log Derived)
	####################

	def GameBoot(self, timestamp):
		net.sendData('GameBoot {{"timestamp":{0}}}'.format(timestamp))

	def RunStart(self, timestamp, seed):
		net.sendData('RunStart {{"timestamp":{0}, "seed":"{1}"}}'.format(timestamp, seed))

	def ResetsOver(self, timestamp):
		net.sendData('ResetsOver {{"timestamp":{0}}}'.format(timestamp))

	def StartCharacter(self, timestamp, character):
		net.sendData('StartCharacter {{"timestamp":{0}, "character":"{1}"}}'.format(timestamp, character))

	def FloorChange(self, timestamp, floor, variant):
		net.sendData('FloorChange {{"timestamp":{0}, "floor":"{1}", "variant":"{2}"}}'.format(timestamp, floor, variant))

	def GetItem(self, timestamp, item, name):
		net.sendData('GetItem {{"timestamp":{0}, "item":"{1}", "name":"{2}"}}'.format(timestamp, item, name))

	def FloorBoss(self, timestamp, roomID, name):
		net.sendData('FloorBoss {{"timestamp":{0}, "roomID":"{1}", "name":"{2}"}}'.format(timestamp, roomID, name))

	def EnterRoom(self, timestamp, roomID, name):
		net.sendData('EnterRoom {{"timestamp":{0}, "roomID":"{1}", "name":"{2}"}}'.format(timestamp, roomID, name))

	def SpawnEntity(self, timestamp, type, variant):
		net.sendData('SpawnEntity {{"timestamp":{0}, "type":"{1}", "variant":"{2}"}}'.format(timestamp, type, variant))

	def BossDeath(self, timestamp):
		net.sendData('BossDeath {{"timestamp":{0}}}'.format(timestamp))

	def RunComplete(self, timestamp, index, name):
		net.sendData('RunComplete {{"timestamp":{0}, "index":"{1}", "name":"{2}"}}'.format(timestamp, index, name))

	def Ripperoni(self, timestamp, killed_by):
		net.sendData('Ripperoni {{"timestamp":{0}, "killed_by":"{1}"}}'.format(timestamp, killed_by))

	def BackToMenu(self, timestamp):
		net.sendData('BackToMenu {{"timestamp":{0}}}'.format(timestamp))

	def Krampus(self, timestamp):
		net.sendData('Krampus {{"timestamp":{0}}}'.format(timestamp))

	def AngelDeal(self, timestamp):
		net.sendData('AngelDeal {{"timestamp":{0}}}'.format(timestamp))

	def DevilDeal(self, timestamp):
		net.sendData('DevilDeal {{"timestamp":{0}}}'.format(timestamp))

	####################
	# Incoming Commands
	####################

	def parseMessage(self, message):
		try:
			print ("Recv Msg: {0}".format(message))

			command = message.split(" ", 1)
			body = json.loads(command[1])

			if command[0] == "roomList":
				self.RoomList.emit(body["room"], body["users"])

			elif command[0] == "raceList":
				self.RaceList.emit(body["races"])

			elif command[0] == "racerList":
				self.RacerList.emit(body["race_id"], body["racers"])

			elif command[0] == "success":
				self.Success.emit(body["type"], body["msg"])

			elif command[0] == "error":
				self.Error.emit(body["type"], body["msg"])
				QMessageBox.warning(mainWindow, "Error", body["msg"])

			elif command[0] == "roomMessage":
				self.RoomMessage.emit(body["to"], body["from"], body["msg"])

			elif command[0] == "raceServer":
				self.RaceServer.emit(body["id"], body["msg"])

			else:
				print ("Unknown Command: '{0}'".format(message))

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
		net.login("Chronometrics", "test")
		net.connection.connected.connect(self.loginComplete)

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

		# Setup the tabs
		self.tabs = QTabWidget()

		self.tabs.setTabShape(QTabWidget.Triangular)
		self.tabs.setTabsClosable(True)
		self.tabs.setMovable(True)

		self.tabs.tabCloseRequested.connect(self.closeTab)

		self.tabs.addTab(RoomTab("global", self.tabs), "global")

		# Setup the user command buttons
		logout = QPushButton("Logout")
		joinRoom = QPushButton("Join Room")
		newRace = QPushButton("New Race")

		logout.released.connect(self.logout)
		joinRoom.released.connect(self.joinRoom)
		newRace.released.connect(self.newRace)

		# Setup the layouts for all widgets
		buttons = QHBoxLayout()
		buttons.addWidget(newRace)
		buttons.addWidget(joinRoom)
		buttons.addWidget(logout)

		layout = QVBoxLayout()
		layout.addWidget(self.tabs)
		layout.addLayout(buttons)

		self.setLayout(layout)

		# Callback for race creation
		server.Success.connect(self.raceCallback)

	def closeTab(self, index):
		tab = self.tabs.widget(index)

		if type(tab) is RoomTab:
			server.roomLeave(tab.name)
		elif type(tab) is RaceTab:
			server.raceLeave(tab.id)

		self.tabs.removeTab(index)

	def logout(self):
		server.logout()
		mainWindow.setCentralWidget(LoginScreen())

	def newRace(self):
		dialog = QInputDialog()
		raceName, completed = dialog.getText(self, "New Race", "Choose a name for your race.")

		if completed:
			server.raceCreate(raceName)

	def raceCallback(self, msgtype, msg):
		if msgtype == "raceJoin":
			tabWidget = RaceTab(msg["name"], self.tabs, msg["id"])

			self.tabs.addTab(tabWidget, msg["name"])

		elif msgtype == "raceCreate":
			icon = QIcon("resources/flag-checker.png")
			tabWidget = RaceTab(msg["name"], self.tabs, msg["id"])

			self.tabs.addTab(tabWidget, icon, msg["name"])

	def joinRoom(self):
		dialog = QInputDialog()
		roomName, completed = dialog.getText(self, "Join Room", "Enter the name of the room to join.")

		if completed:
			server.roomJoin(roomName)
			self.tabs.addTab(RoomTab(roomName, self.tabs), roomName)


# A Room or Race tab
class RoomTab(QWidget):

	def __init__(self, name, tabs):
		QWidget.__init__(self)
		self.name = name
		self.tabs = tabs

		# Widget Setup
		self.chat = QListWidget()
		self.chatEntry = QLineEdit()
		self.userList = QListWidget()

		self.chatEntry.returnPressed.connect(self.sendMessage)

		# RaceList Tree Setup
		self.raceList = QTreeWidget()

		self.raceList.setColumnCount(6) # Button, Name, Type, Ruleset, Status, Created By
		self.raceList.setHeaderLabels(["Name", "", "Type", "Ruleset", "Status", "Created By"])

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
			icon = QIcon()
			if user["admin"] == 1:
				icon = QIcon("resources/cheese.png")
			elif user["squelched"] == 1:
				icon = QIcon("resources/poop.png")

			item = QListWidgetItem(icon, user["name"])
			self.userList.addItem(item)

		self.userList.sortItems()

	def updateRacelist(self, races):
		self.raceList.clear()

		for race in races:
			item = QTreeWidgetItem([race["name"], "", race["ruleset"], "Diversity", race["status"], race["captain"]])
			item.joinButton = QPushButton("Join")
			item.joinButton.raceID = race["id"]
			
			self.raceList.addTopLevelItem(item)
			self.raceList.setItemWidget(item, 1, item.joinButton)

			item.joinButton.released.connect(self.joinRace)

		self.raceList.sortItems(0, Qt.AscendingOrder)

	def updateChat(self, to, afrom, msg):
		if to != self.name: return

		self.chat.addItem("{0}: {1}".format(afrom, msg))

	def sendMessage(self):
		server.roomMessage(self.name, self.chatEntry.text())
		self.chatEntry.clear()

	def joinRace(self):
		index = self.sender().raceID
		server.raceJoin(index)


# Represents the Game ruleset and pregame area
class RaceTab(QWidget):

	def __init__(self, name, tabs, id=0):
		QWidget.__init__(self)

		self.name = name
		self.tabs = tabs
		self.id = id

		# Widget Setup
		self.chat = QListWidget()
		self.chatEntry = QLineEdit()
		self.userList = QListWidget()

		self.chatEntry.returnPressed.connect(self.sendMessage)
		server.RoomMessage.connect(self.updateChat)
		server.RoomList.connect(self.updateUserlist)

		self.readyButton = QPushButton("Ready")
		self.readyButton.released.connect(self.toggleReady)

		# Layout Setup
		chatLayout = QVBoxLayout()
		chatLayout.addWidget(self.chat)
		chatLayout.addWidget(self.chatEntry)

		userLayout = QVBoxLayout()
		userLayout.addWidget(self.readyButton)
		userLayout.addWidget(self.userList)
		# userLayout.setSpacing(0)

		layout = QHBoxLayout()
		layout.addLayout(chatLayout)
		layout.addLayout(userLayout)
	
		self.setLayout(layout)

	def toggleReady(self):
		if self.readyButton.text() == "Ready":
			self.readyButton.setText("Unready")
			server.raceReady(self.id)
		else:
			self.readyButton.setText("Ready")
			server.raceUnready(self.id)

	def updateUserlist(self, room, users):
		if room != self.name: return

		self.userList.clear()

		for user in users:

			self.userList.addItem(user["name"])

		self.userList.sortItems()

	def updateChat(self, to, afrom, msg):
		if to != "_race_{0}".format(self.id): return

		self.chat.addItem("{0}: {1}".format(afrom, msg))

	def sendMessage(self):
		server.roomMessage("_race_{0}".format(self.id), self.chatEntry.text())
		self.chatEntry.clear()


# Represents the Isaac Game
class IsaacScene(QWidget):

	# Start up the race
	def __init__(self, racers, logParser = None, darkRoom = False):
		QWidget.__init__(self)

		# Timer
		self.startTime = QDateTime.currentDateTime()
		self.startTimer(0)
		self.timerText = QLabel("00:00:00:000")

		self.timerText.setAlignment(Qt.AlignHCenter)
		self.timerText.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken);
		font = self.timerText.font()
		font.setPixelSize(48)
		self.timerText.setFont(font)

		# Messsages to send

		# Floor messages
		floorButton = QPushButton("Next Floor")
		floorButton.released.connect(self.newFloor)

		self.floors = ["B1", "B2", "C1", "C2", "D1", "D2", "W1", "W2", "Cath", "Chest"]

		if darkRoom:
			self.floors = ["B1", "B2", "C1", "C2", "D1", "D2", "W1", "W2", "Sheol", "Dark"]

		self.floorIndex = 0

		# Item messages
		itemButton = QPushButton("Get Random Item")
		itemButton.released.connect(self.newItem)

		# Recieving messages
		# server.

		# Setup the List
		self.setupRacerList(racers)

		# Layout
		layout = QVBoxLayout()
		layout.addWidget(self.timerText)
		layout.addWidget(self.racerList)

		self.setLayout(layout)

		# Game State
		self.state = {"bossMet": False, "bossCleared": False, "reseting": False, "roomCount": 0, "started": False}

		# Log Parser
		self.logParser = logParser
		if not logParser:
			self.logParser = LogParser()

		self.setupRaceSignals()

	# Setup the list of racers
	def setupRacerList(self, racers):
		self.racerList = QTreeWidget()

		self.racerList.setColumnCount(4) # Icon, Name, Floor, Time Offset, Items
		self.racerList.setHeaderLabels(["Name", "Status", "Offset", "Items"])
		self.racerList.setIconSize(QSize(36, 36))

		self.racerList.setColumnWidth(0, 160)
		self.racerList.setIndentation(0)

		for racer in racers:
			item = QTreeWidgetItem([racer, self.floors[self.floorIndex], "±00:00:000", ""])

			# Set the Racer Icon and the Item Icons (???)
			item.setIcon(0, QIcon("resources/racer.png"))
			item.setIcon(3, QIcon("resources/items/105.png"))

			item.setTextAlignment(1, Qt.AlignHCenter)
			font = item.font(1)
			font.setBold(True)
			font.setPixelSize(30)
			item.setFont(1, font)

			self.racerList.addTopLevelItem(item)

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

	# Gets the elapsed time in msecs
	def getTime(self):
		return self.startTime.msecsTo(QDateTime.currentDateTime())

	# Timer Update
	def timerEvent(self, event):
		# Handle the time display
		time = self.getTime()

		h = int(time / 1000 / 60 / 60)
		m = int((time / 1000 / 60) - (h * 60))
		s = int((time / 1000) - ((m + (h * 60))* 60))
		ms = time & 1000

		curTime = "{0:02}:{1:02}:{2:02}:{3:03}".format(h,m,s,ms)

		self.timerText.setText(curTime)

		# Handle the log parsing
		self.logParser.updateLog()

	##################
	# Here be Signals
	##################

	def setupRaceSignals(self):
		self.logParser.GameBoot.connect(self.GameBoot)
		self.logParser.RunStart.connect(self.RunStart)
		self.logParser.StartCharacter.connect(self.StartCharacter)
		self.logParser.FloorChange.connect(self.FloorChange)
		self.logParser.GetItem.connect(self.GetItem)
		self.logParser.FloorBoss.connect(self.FloorBoss)
		self.logParser.EnterRoom.connect(self.EnterRoom)
		self.logParser.SpawnEntity.connect(self.SpawnEntity)
		self.logParser.BossDeath.connect(self.BossDeath)
		self.logParser.RunComplete.connect(self.RunComplete)
		self.logParser.Ripperoni.connect(self.Ripperoni)
		self.logParser.BackToMenu.connect(self.BackToMenu)
		self.logParser.Krampus.connect(self.Krampus)
		self.logParser.AngelDeal.connect(self.AngelDeal)
		self.logParser.DevilDeal.connect(self.DevilDeal)

	def GameBoot(self):
		server.GameBoot(self.getTime())

	def RunStart(self, seed):
		if not self.state["started"]:
			server.RunStart(self.getTime(), seed)
			self.state["started"] = True

	def StartCharacter(self, character):
		server.StartCharacter(self.getTime(), character)

	def FloorChange(self, floor, variant):
		server.FloorChange(self.getTime(), floor, variant)
		self.state["bossMet"] = False
		self.state["bossCleared"] = False

	def GetItem(self, item, name):
		server.GetItem(self.getTime(), item, name)

	def FloorBoss(self, roomID, name):
		if self.state["bossMet"] == False:
			self.state["bossMet"] = True
			server.FloorBoss(self.getTime(), roomID, name)

	def EnterRoom(self, roomID, name):
		server.EnterRoom(self.getTime(), roomID, name)

		self.state["roomCount"] = self.state["roomCount"] + 1

		if self.state["roomCount"] == 5:
			server.ResetsOver(self.getTime())

	def SpawnEntity(self, type, variant):
		server.SpawnEntity(self.getTime(), type, variant)

	def BossDeath(self):
		if self.state["bossMet"] == True and self.state["bossCleared"] == False:
			server.BossDeath(self.getTime())
			self.state["bossCleared"] = True

	def RunComplete(self, index, name):
		if index > 10:
			server.RunComplete(self.getTime(), index, name)

	def Ripperoni(self, killed_by):
		server.Ripperoni(self.getTime(), killed_by)

	def BackToMenu(self):
		server.BackToMenu(self.getTime())

	def Krampus(self):
		server.Krampus(self.getTime())

	def AngelDeal(self):
		server.AngelDeal(self.getTime())

	def DevilDeal(self):
		server.DevilDeal(self.getTime())


# Grabs the log.txt, and allows it to be parsed.
class LogParser(QObject):

	# Singals for all the game events
	GameBoot 		= pyqtSignal() 				# 
	RunStart		= pyqtSignal(str)			# (seed)
	StartCharacter	= pyqtSignal(int)			# (character index)
	FloorChange		= pyqtSignal(int, int)		# (floor, variant)
	GetItem			= pyqtSignal(int, str)		# (item, name)
	FloorBoss		= pyqtSignal(int, str)		# (roomId, name)
	EnterRoom		= pyqtSignal(float, str)	# (roomId, name)
	SpawnEntity		= pyqtSignal(int, int)		# (type, variant)
	BossDeath		= pyqtSignal()				# 
	RunComplete		= pyqtSignal(int, str)		# (index, name)
	Ripperoni		= pyqtSignal(float)			# (Entity who killed you)
	BackToMenu		= pyqtSignal()				# 
	Krampus			= pyqtSignal()				# 
	AngelDeal		= pyqtSignal()				# 
	DevilDeal		= pyqtSignal()				# 
	
	def __init__(self):
		QObject.__init__(self)

		self.logPath = ""
		self.log = None
		self.logSize = 0
		self.currentLine = 0

		self.openLog()

	# Opens the log file
	def openLog(self):

		# Get the system specific log.txt path
		if self.logPath == "":
			if platform.system() == "Darwin":
				self.logPath = os.path.expanduser('~') + '/Library/Application Support/Binding of Isaac Afterbirth/log.txt'

			elif platform.system() == "Windows":
				self.logPath = os.environ['USERPROFILE'] + '/Documents/My Games/Binding of Isaac Afterbirth/log.txt'

			elif platform.system() == "Linux":
				self.logPath = os.getenv('XDG_DATA_HOME', os.path.expanduser('~') + '/.local/share') + '/binding of isaac afterbirth/log.txt'

	# Reloads the file data
	def updateLog(self):

		# if the log.txt exists...
		if os.path.exists(self.logPath):

			# Check to see if the file has changed before opening it
			size = os.path.getsize(self.logPath)
			if size != self.logSize:
				self.log = open(self.logPath, 'r').read()
				self.logSize = size

				# Since we're updating it, we need to parse it right away
				self.parseLog()

		# No log found, throw an error
		else:
			QMessageBox.warning(mainWindow, "Error", "Isaac data and saves not found. We are unable to start your race without these files. If your Isaac is properly installed and you have started a run at least once but still get this error, report this to the administration.")

	# Begins parsing the logfile
	def parseLog(self):

		# Split everything into lines
		lines = self.log.splitlines()

		# Iterate over the new lines, parse them, and then send the appropriate signal
		for line in lines[self.currentLine:]:

			# GameBoot
			if "Binding of Isaac: Afterbirth" in line:
				self.GameBoot.emit()

			# RunStart
			elif "RNG Start Seed" in line:
				seed = line[16:25]
				self.RunStart.emit(seed)

			# StartCharacter
			elif "Initialized player" in line:
				character = int(line[-1:])
				self.StartCharacter.emit(character)

			# FloorChange
			elif "Level::Init" in line:
				t = re.search("Level::Init m_Stage (\d+), m_StageType (\d+)", line)
				self.FloorChange.emit(int(t.group(1)), int(t.group(2)))

			# GetItem
			elif "Adding collectible" in line:
				t = re.search("Adding collectible (\d+) \((.*)\)", line)
				self.GetItem.emit(int(t.group(1)), t.group(2))

			# Krampus
			elif "(Krampus" in line:
				self.Krampus.emit()

			# AngelDeal
			elif "(Devil" in line:
				self.AngelDeal.emit()

			# DevilDeal
			elif "(Angel" in line:
				self.DevilDeal.emit()

			# FloorBoss
			elif "Room 5." in line:
				t = re.search("Room 5.(\d+)\((.*)\)", line)
				self.FloorBoss.emit(int(t.group(1)), t.group(2))

			# NewRoom
			elif "Room " in line:
				t = re.search("Room ([0-9.]+)\((.*)\)", line)
				self.EnterRoom.emit(float(t.group(1)), t.group(2))

			# SpawnEntity
			elif "Spawn Entity" in line:
				t = re.search("Spawn Entity with Type\((\d+)\), Variant\((\d+)\).*", line)
				self.SpawnEntity.emit(int(t.group(1)), int(t.group(2)))

			# BossDeath
			elif "TriggerBossDeath: 0 bosses remaining." in line:
				self.BossDeath.emit()

			# RunComplete
			elif "playing cutscene" in line:
				t = re.search("playing cutscene (\d+) \((.*)\).", line)
				self.RunComplete.emit(int(t.group(1)), t.group(2))

			# Ripperoni
			elif "Game Over" in line:
				t = re.search("Game Over. Killed by \(([0-9.]+)\)", line)
				self.Ripperoni.emit(float(t.group(1)))

			# BackToMenu
			elif "Different number of achievements" in line:
				self.BackToMenu.emit()

		# update line count
		self.currentLine = len(lines)


# Main Window Class. Just used for containers
class MainWindow(QMainWindow):

	# Setup the window
	def __init__(self):
		QMainWindow.__init__(self)

		self.setWindowTitle('Isaac Client')
		self.setIconSize(QSize(16, 16))
		self.setGeometry(100, 500, 800, 450)

		self.setCentralWidget(IsaacScene(["Chronometrics", "Zamiell"]))

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
