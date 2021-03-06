from PySide import QtCore, QtGui
from PySide.QtCore import QSettings, Qt, QCoreApplication, QUrl
from PySide.QtGui import QApplication, QLineEdit, QCursor, QLabel, QCheckBox, QDesktopServices, QIcon, QImage, QButtonGroup, QRadioButton, QDoubleSpinBox
from syncplay.players.playerFactory import PlayerFactory
from datetime import datetime
import os
import sys
from syncplay.messages import getMessage, getLanguages, setLanguage, getInitialLanguage
from syncplay import constants

class GuiConfiguration:
    def __init__(self, config, error=None, defaultConfig=None):
        self.defaultConfig = defaultConfig
        self.config = config
        self._availablePlayerPaths = []
        self.error = error

    def run(self):
        if QCoreApplication.instance() is None:
            self.app = QtGui.QApplication(sys.argv)
        dialog = ConfigDialog(self.config, self._availablePlayerPaths, self.error, self.defaultConfig)
        dialog.exec_()

    def setAvailablePaths(self, paths):
        self._availablePlayerPaths = paths

    def getProcessedConfiguration(self):
        return self.config

    class WindowClosed(Exception):
        pass

class ConfigDialog(QtGui.QDialog):

    pressedclosebutton = False
    moreToggling = False

    def automaticUpdatePromptCheck(self):
        if self.automaticupdatesCheckbox.checkState() == Qt.PartiallyChecked and not self.nostoreCheckbox.isChecked():
            reply = QtGui.QMessageBox.question(self, "Syncplay",
                    getMessage("promptforupdate-label"), QtGui.QMessageBox.StandardButton.Yes | QtGui.QMessageBox.StandardButton.No)
            if reply == QtGui.QMessageBox.Yes:
                self.automaticupdatesCheckbox.setChecked(True)
            else:
                self.automaticupdatesCheckbox.setChecked(False)

    def moreToggled(self):
        if self.moreToggling == False:
            self.moreToggling = True

            if self.showmoreCheckbox.isChecked():
                self.tabListFrame.show()
                self.resetButton.show()
                self.nostoreCheckbox.show()
                self.saveMoreState(True)
                self.tabListWidget.setCurrentRow(0)
                self.ensureTabListIsVisible()
            else:
                self.tabListFrame.hide()
                self.resetButton.hide()
                self.nostoreCheckbox.hide()
                self.saveMoreState(False)
                self.stackedLayout.setCurrentIndex(0)

            self.adjustSize()
            self.setFixedSize(self.sizeHint())
        self.moreToggling = False
        self.setFixedWidth(self.minimumSizeHint().width())
        self.executablepathCombobox.setFixedWidth(self.mediapathTextbox.width())

    def runButtonTextUpdate(self):
        if self.nostoreCheckbox.isChecked():
            self.runButton.setText(getMessage("run-label"))
        else:
            self.runButton.setText(getMessage("storeandrun-label"))

    def openHelp(self):
        self.QtGui.QDesktopServices.openUrl(QUrl("http://syncplay.pl/guide/client/"))

    def _isURL(self, path):
        if path is None:
            return False

        if "http://" in path:
            return True

    def safenormcaseandpath(self, path):
        if self._isURL(path):
            return path
        else:
            return os.path.normcase(os.path.normpath(path))

    def _tryToFillPlayerPath(self, playerpath, playerpathlist):
        settings = QSettings("Syncplay", "PlayerList")
        settings.beginGroup("PlayerList")
        savedPlayers = settings.value("PlayerList", [])
        if not isinstance(savedPlayers, list):
            savedPlayers = []
        else:
            for i, savedPlayer in enumerate(savedPlayers):
                savedPlayers[i] = self.safenormcaseandpath(savedPlayer)
        playerpathlist = list(set(playerpathlist + savedPlayers))
        settings.endGroup()
        foundpath = ""

        if playerpath != None and playerpath != "":
            if self._isURL(playerpath):
                foundpath = playerpath
                self.executablepathCombobox.addItem(foundpath)

            else:
                if not os.path.isfile(playerpath):
                    expandedpath = PlayerFactory().getExpandedPlayerPathByPath(playerpath)
                    if expandedpath != None and os.path.isfile(expandedpath):
                        playerpath = expandedpath

                if os.path.isfile(playerpath):
                    foundpath = playerpath
                    self.executablepathCombobox.addItem(foundpath)

        for path in playerpathlist:
            if self._isURL(path):
                if foundpath == "":
                    foundpath = path
                if path != playerpath:
                    self.executablepathCombobox.addItem(path)

            elif os.path.isfile(path) and os.path.normcase(os.path.normpath(path)) != os.path.normcase(os.path.normpath(foundpath)):
                self.executablepathCombobox.addItem(path)
                if foundpath == "":
                    foundpath = path

        if foundpath != "":
            settings.beginGroup("PlayerList")
            playerpathlist.append(self.safenormcaseandpath(foundpath))
            settings.setValue("PlayerList", list(set(playerpathlist)))
            settings.endGroup()
        return foundpath

    def updateExecutableIcon(self):
        currentplayerpath = unicode(self.executablepathCombobox.currentText())
        iconpath = PlayerFactory().getPlayerIconByPath(currentplayerpath)
        if iconpath != None and iconpath != "":
            self.executableiconImage.load(self.resourcespath + iconpath)
            self.executableiconLabel.setPixmap(QtGui.QPixmap.fromImage(self.executableiconImage))
        else:
            self.executableiconLabel.setPixmap(QtGui.QPixmap.fromImage(QtGui.QImage()))

    def languageChanged(self):
        setLanguage(unicode(self.languageCombobox.itemData(self.languageCombobox.currentIndex())))
        QtGui.QMessageBox.information(self, "Syncplay", getMessage("language-changed-msgbox-label"))

    def browsePlayerpath(self):
        options = QtGui.QFileDialog.Options()
        defaultdirectory = ""
        browserfilter = "All files (*)"

        if os.name == 'nt':
            browserfilter = "Executable files (*.exe);;All files (*)"
            if "PROGRAMFILES(X86)" in os.environ:
                defaultdirectory = os.environ["ProgramFiles(x86)"]
            elif "PROGRAMFILES" in os.environ:
                defaultdirectory = os.environ["ProgramFiles"]
            elif "PROGRAMW6432" in os.environ:
                defaultdirectory = os.environ["ProgramW6432"]
        elif sys.platform.startswith('linux'):
            defaultdirectory = "/usr/bin"
        elif sys.platform.startswith('darwin'):
            defaultdirectory = "/Applications/"
        elif "bsd" in sys.platform or sys.platform.startswith('dragonfly'):
            defaultdirectory = "/usr/local/bin"

        fileName, filtr = QtGui.QFileDialog.getOpenFileName(self,
                "Browse for media player executable",
                defaultdirectory,
                browserfilter, "", options)
        if fileName:
            self.executablepathCombobox.setEditText(os.path.normpath(fileName))

    def loadLastUpdateCheckDate(self):
        settings = QSettings("Syncplay", "Interface")
        settings.beginGroup("Update")
        self.lastCheckedForUpdates = settings.value("lastChecked", None)
        if self.lastCheckedForUpdates:
            if self.config["lastCheckedForUpdates"] is not None and self.config["lastCheckedForUpdates"] is not "":
                if self.lastCheckedForUpdates > datetime.strptime(self.config["lastCheckedForUpdates"], "%Y-%m-%d %H:%M:%S.%f"):
                    self.config["lastCheckedForUpdates"] = str(self.lastCheckedForUpdates)
            else:
                self.config["lastCheckedForUpdates"] = str(self.lastCheckedForUpdates)

    def loadMediaBrowseSettings(self):
        settings = QSettings("Syncplay", "MediaBrowseDialog")
        settings.beginGroup("MediaBrowseDialog")
        self.mediadirectory = settings.value("mediadir", "")
        settings.endGroup()

    def saveMediaBrowseSettings(self):
        settings = QSettings("Syncplay", "MediaBrowseDialog")
        settings.beginGroup("MediaBrowseDialog")
        settings.setValue("mediadir", self.mediadirectory)
        settings.endGroup()

    def getMoreState(self):
        settings = QSettings("Syncplay", "MoreSettings")
        settings.beginGroup("MoreSettings")
        morestate = unicode.lower(unicode(settings.value("ShowMoreSettings", "false")))
        settings.endGroup()
        if morestate == "true":
            return True
        else:
            return False

    def saveMoreState(self, morestate):
        settings = QSettings("Syncplay", "MoreSettings")
        settings.beginGroup("MoreSettings")
        settings.setValue("ShowMoreSettings", morestate)
        settings.endGroup()

    def browseMediapath(self):
        self.loadMediaBrowseSettings()
        options = QtGui.QFileDialog.Options()
        if os.path.isdir(self.mediadirectory):
            defaultdirectory = self.mediadirectory
        elif os.path.isdir(QDesktopServices.storageLocation(QDesktopServices.MoviesLocation)):
            defaultdirectory = QDesktopServices.storageLocation(QDesktopServices.MoviesLocation)
        elif os.path.isdir(QDesktopServices.storageLocation(QDesktopServices.HomeLocation)):
            defaultdirectory = QDesktopServices.storageLocation(QDesktopServices.HomeLocation)
        else:
            defaultdirectory = ""
        browserfilter = "All files (*)"
        fileName, filtr = QtGui.QFileDialog.getOpenFileName(self, "Browse for media files", defaultdirectory,
                browserfilter, "", options)
        if fileName:
            self.mediapathTextbox.setText(os.path.normpath(fileName))
            self.mediadirectory = os.path.dirname(fileName)
            self.saveMediaBrowseSettings()

    def _saveDataAndLeave(self):
        self.automaticUpdatePromptCheck()
        self.loadLastUpdateCheckDate()

        self.processWidget(self, lambda w: self.saveValues(w))
        if self.hostTextbox.text():
            self.config['host'] = self.hostTextbox.text() if ":" in self.hostTextbox.text() else self.hostTextbox.text() + ":" + unicode(constants.DEFAULT_PORT)
        else:
            self.config['host'] = None
        self.config['playerPath'] = unicode(self.safenormcaseandpath(self.executablepathCombobox.currentText()))
        self.config['language'] = unicode(self.languageCombobox.itemData(self.languageCombobox.currentIndex()))
        if self.mediapathTextbox.text() == "":
            self.config['file'] = None
        elif os.path.isfile(os.path.abspath(self.mediapathTextbox.text())):
            self.config['file'] = os.path.abspath(self.mediapathTextbox.text())
        else:
            self.config['file'] = unicode(self.mediapathTextbox.text())

        if not self.slowdownThresholdSpinbox.text:
            self.slowdownThresholdSpinbox.value = constants.DEFAULT_SLOWDOWN_KICKIN_THRESHOLD
        if not self.rewindThresholdSpinbox.text:
            self.rewindThresholdSpinbox.value = constants.DEFAULT_REWIND_THRESHOLD
        if not self.fastforwardThresholdSpinbox.text:
            self.fastforwardThresholdSpinbox.value = constants.DEFAULT_FASTFORWARD_THRESHOLD
        self.config['slowdownThreshold'] = self.slowdownThresholdSpinbox.value()
        self.config['rewindThreshold'] = self.rewindThresholdSpinbox.value()
        self.config['fastforwardThreshold'] = self.fastforwardThresholdSpinbox.value()

        self.pressedclosebutton = True
        self.close()
        return

    def closeEvent(self, event):
        if self.pressedclosebutton == False:
            sys.exit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
           sys.exit()

    def dragEnterEvent(self, event):
        data = event.mimeData()
        urls = data.urls()
        if urls and urls[0].scheme() == 'file':
            event.acceptProposedAction()

    def dropEvent(self, event):
        data = event.mimeData()
        urls = data.urls()
        if urls and urls[0].scheme() == 'file':
            dropfilepath = os.path.abspath(unicode(event.mimeData().urls()[0].toLocalFile()))
            if dropfilepath[-4:].lower() == ".exe":
                self.executablepathCombobox.setEditText(dropfilepath)
            else:
                self.mediapathTextbox.setText(dropfilepath)

    def processWidget(self, container, torun):
        for widget in container.children():
            self.processWidget(widget, torun)
            if hasattr(widget, 'objectName') and widget.objectName() and widget.objectName()[:3] != "qt_":
                torun(widget)

    def loadTooltips(self, widget):
        tooltipName = widget.objectName().lower().split(constants.CONFIG_NAME_MARKER)[0] + "-tooltip"
        if tooltipName[:1] == constants.INVERTED_STATE_MARKER or tooltipName[:1] == constants.LOAD_SAVE_MANUALLY_MARKER:
            tooltipName = tooltipName[1:]
        widget.setToolTip(getMessage(tooltipName))

    def loadValues(self, widget):
        valueName = str(widget.objectName())
        if valueName[:1] == constants.LOAD_SAVE_MANUALLY_MARKER:
            return

        if isinstance(widget, QCheckBox) and widget.objectName():
            if valueName[:1] == constants.INVERTED_STATE_MARKER:
                valueName = valueName[1:]
                inverted = True
            else:
                inverted = False
            if self.config[valueName] is None:
                widget.setTristate(True)
                widget.setCheckState(Qt.PartiallyChecked)
                widget.stateChanged.connect(lambda: widget.setTristate(False))
            else:
                widget.setChecked(self.config[valueName] != inverted)
        elif isinstance(widget, QRadioButton):
            radioName, radioValue  = valueName.split(constants.CONFIG_NAME_MARKER)[1].split(constants.CONFIG_VALUE_MARKER)
            if self.config[radioName] == radioValue:
                widget.setChecked(True)
        elif isinstance(widget, QLineEdit):
            widget.setText(self.config[valueName])

    def saveValues(self, widget):
        valueName = str(widget.objectName())
        if valueName[:1] == constants.LOAD_SAVE_MANUALLY_MARKER:
            return

        if isinstance(widget, QCheckBox) and widget.objectName():
            if widget.checkState() == Qt.PartiallyChecked:
                self.config[valueName] = None
            else:
                if valueName[:1] == constants.INVERTED_STATE_MARKER:
                    valueName = valueName[1:]
                    inverted = True
                else:
                    inverted = False
                self.config[valueName] = widget.isChecked() != inverted
        elif isinstance(widget, QRadioButton):
            radioName, radioValue  = valueName.split(constants.CONFIG_NAME_MARKER)[1].split(constants.CONFIG_VALUE_MARKER)
            if widget.isChecked():
                self.config[radioName] = radioValue
        elif isinstance(widget, QLineEdit):
            self.config[valueName] = widget.text()

    def connectChildren(self, widget):
        widgetName = str(widget.objectName())
        if self.subitems.has_key(widgetName) and isinstance(widget, QCheckBox):
            widget.stateChanged.connect(lambda: self.updateSubwidgets(self, widget))
            self.updateSubwidgets(self, widget)

    def updateSubwidgets(self, container, parentwidget, subwidgets=None):
        widgetName = parentwidget.objectName()
        if not subwidgets:
            subwidgets = self.subitems[widgetName]
        for widget in container.children():
            self.updateSubwidgets(widget, parentwidget, subwidgets)
            if hasattr(widget, 'objectName') and widget.objectName() and widget.objectName() in subwidgets:
                widget.setDisabled(not parentwidget.isChecked())

    def addBasicTab(self):
        config = self.config
        playerpaths = self.playerpaths
        resourcespath = self.resourcespath
        error = self.error
        if self.datacleared == True:
            error = constants.ERROR_MESSAGE_MARKER + "{}".format(getMessage("gui-data-cleared-notification"))
        if config['host'] == None:
            host = ""
        elif ":" in config['host']:
            host = config['host']
        else:
            host = config['host'] + ":" + str(config['port'])

        self.connectionSettingsGroup = QtGui.QGroupBox(getMessage("connection-group-title"))
        self.hostTextbox = QLineEdit(host, self)
        self.hostLabel = QLabel(getMessage("host-label"), self)
        self.usernameTextbox = QLineEdit(self)
        self.usernameTextbox.setObjectName("name")
        self.serverpassLabel = QLabel(getMessage("password-label"), self)
        self.defaultroomTextbox = QLineEdit(self)
        self.usernameLabel = QLabel(getMessage("name-label"), self)
        self.serverpassTextbox = QLineEdit(self)
        self.defaultroomLabel = QLabel(getMessage("room-label"), self)

        self.hostLabel.setObjectName("host")
        self.hostTextbox.setObjectName(constants.LOAD_SAVE_MANUALLY_MARKER + "host")
        self.usernameLabel.setObjectName("name")
        self.usernameTextbox.setObjectName("name")
        self.serverpassLabel.setObjectName("password")
        self.serverpassTextbox.setObjectName("password")
        self.defaultroomLabel.setObjectName("room")
        self.defaultroomTextbox.setObjectName("room")

        self.connectionSettingsLayout = QtGui.QGridLayout()
        self.connectionSettingsLayout.addWidget(self.hostLabel, 0, 0)
        self.connectionSettingsLayout.addWidget(self.hostTextbox, 0, 1)
        self.connectionSettingsLayout.addWidget(self.serverpassLabel, 1, 0)
        self.connectionSettingsLayout.addWidget(self.serverpassTextbox, 1, 1)
        self.connectionSettingsLayout.addWidget(self.usernameLabel, 2, 0)
        self.connectionSettingsLayout.addWidget(self.usernameTextbox, 2, 1)
        self.connectionSettingsLayout.addWidget(self.defaultroomLabel, 3, 0)
        self.connectionSettingsLayout.addWidget(self.defaultroomTextbox, 3, 1)
        self.connectionSettingsGroup.setLayout(self.connectionSettingsLayout)
        self.connectionSettingsGroup.setMaximumHeight(self.connectionSettingsGroup.minimumSizeHint().height())

        self.mediaplayerSettingsGroup = QtGui.QGroupBox(getMessage("media-setting-title"))
        self.executableiconImage = QtGui.QImage()
        self.executableiconLabel = QLabel(self)
        self.executableiconLabel.setMinimumWidth(16)
        self.executablepathCombobox = QtGui.QComboBox(self)
        self.executablepathCombobox.setEditable(True)
        self.executablepathCombobox.currentIndexChanged.connect(self.updateExecutableIcon)
        self.executablepathCombobox.setEditText(self._tryToFillPlayerPath(config['playerPath'], playerpaths))
        self.executablepathCombobox.setFixedWidth(165)
        self.executablepathCombobox.editTextChanged.connect(self.updateExecutableIcon)

        self.executablepathLabel = QLabel(getMessage("executable-path-label"), self)
        self.executablebrowseButton = QtGui.QPushButton(QtGui.QIcon(resourcespath + 'folder_explore.png'), getMessage("browse-label"))
        self.executablebrowseButton.clicked.connect(self.browsePlayerpath)
        self.mediapathTextbox = QLineEdit(config['file'], self)
        self.mediapathLabel = QLabel(getMessage("media-path-label"), self)
        self.mediabrowseButton = QtGui.QPushButton(QtGui.QIcon(resourcespath + 'folder_explore.png'), getMessage("browse-label"))
        self.mediabrowseButton.clicked.connect(self.browseMediapath)

        self.executablepathLabel.setObjectName("executable-path")
        self.executablepathCombobox.setObjectName("executable-path")
        self.mediapathLabel.setObjectName("media-path")
        self.mediapathTextbox.setObjectName(constants.LOAD_SAVE_MANUALLY_MARKER + "media-path")

        self.mediaplayerSettingsLayout = QtGui.QGridLayout()
        self.mediaplayerSettingsLayout.addWidget(self.executablepathLabel, 0, 0)
        self.mediaplayerSettingsLayout.addWidget(self.executableiconLabel, 0, 1)
        self.mediaplayerSettingsLayout.addWidget(self.executablepathCombobox, 0, 2)
        self.mediaplayerSettingsLayout.addWidget(self.executablebrowseButton, 0, 3)
        self.mediaplayerSettingsLayout.addWidget(self.mediapathLabel, 1, 0)
        self.mediaplayerSettingsLayout.addWidget(self.mediapathTextbox , 1, 2)
        self.mediaplayerSettingsLayout.addWidget(self.mediabrowseButton , 1, 3)
        self.mediaplayerSettingsGroup.setLayout(self.mediaplayerSettingsLayout)

        self.showmoreCheckbox = QCheckBox(getMessage("more-title"))
        self.showmoreCheckbox.setObjectName(constants.LOAD_SAVE_MANUALLY_MARKER + "more")

        self.basicOptionsFrame = QtGui.QFrame()
        self.basicOptionsLayout = QtGui.QVBoxLayout()
        if error:
            self.errorLabel = QLabel(self)
            if error[:1] != constants.ERROR_MESSAGE_MARKER:
                self.errorLabel.setStyleSheet(constants.STYLE_ERRORLABEL)
            else:
                error = error[1:]
                self.errorLabel.setStyleSheet(constants.STYLE_SUCCESSLABEL)
            self.errorLabel.setText(error)
            self.errorLabel.setAlignment(Qt.AlignCenter)

            self.basicOptionsLayout.addWidget(self.errorLabel, 0, 0)
        self.connectionSettingsGroup.setMaximumHeight(self.connectionSettingsGroup.minimumSizeHint().height())
        self.basicOptionsLayout.setAlignment(Qt.AlignTop)
        self.basicOptionsLayout.addWidget(self.connectionSettingsGroup)
        self.basicOptionsLayout.addSpacing(5)
        self.mediaplayerSettingsGroup.setMaximumHeight(self.mediaplayerSettingsGroup.minimumSizeHint().height())
        self.basicOptionsLayout.addWidget(self.mediaplayerSettingsGroup)

        self.basicOptionsFrame.setLayout(self.basicOptionsLayout)
        self.stackedLayout.addWidget(self.basicOptionsFrame)

    def addMiscTab(self):
        self.miscFrame = QtGui.QFrame()
        self.miscLayout = QtGui.QVBoxLayout()
        self.miscFrame.setLayout(self.miscLayout)

        self.coreSettingsGroup = QtGui.QGroupBox(getMessage("core-behaviour-title"))
        self.coreSettingsLayout = QtGui.QGridLayout()
        self.coreSettingsGroup.setLayout(self.coreSettingsLayout)

        self.pauseonleaveCheckbox = QCheckBox(getMessage("pauseonleave-label"))
        self.pauseonleaveCheckbox.setObjectName("pauseOnLeave")
        self.coreSettingsLayout.addWidget(self.pauseonleaveCheckbox, 0, 0, 1, 4)

        self.alwaysUnpauseCheckbox = QCheckBox(getMessage("alwaysunpause-label"))
        self.alwaysUnpauseCheckbox.setObjectName("alwaysUnpause")
        self.coreSettingsLayout.addWidget(self.alwaysUnpauseCheckbox, 1, 0, 1, 4)

        self.readyatstartCheckbox = QCheckBox(getMessage("readyatstart-label"))
        self.readyatstartCheckbox.setObjectName("readyAtStart")
        self.coreSettingsLayout.addWidget(self.readyatstartCheckbox, 2, 0, 1, 4)

        ### Privacy:

        self.filenameprivacyLabel = QLabel(getMessage("filename-privacy-label"), self)
        self.filenameprivacyButtonGroup = QButtonGroup()
        self.filenameprivacySendRawOption = QRadioButton(getMessage("privacy-sendraw-option"))
        self.filenameprivacySendHashedOption = QRadioButton(getMessage("privacy-sendhashed-option"))
        self.filenameprivacyDontSendOption = QRadioButton(getMessage("privacy-dontsend-option"))
        self.filenameprivacyButtonGroup.addButton(self.filenameprivacySendRawOption)
        self.filenameprivacyButtonGroup.addButton(self.filenameprivacySendHashedOption)
        self.filenameprivacyButtonGroup.addButton(self.filenameprivacyDontSendOption)

        self.filesizeprivacyLabel = QLabel(getMessage("filesize-privacy-label"), self)
        self.filesizeprivacyButtonGroup = QButtonGroup()
        self.filesizeprivacySendRawOption = QRadioButton(getMessage("privacy-sendraw-option"))
        self.filesizeprivacySendHashedOption = QRadioButton(getMessage("privacy-sendhashed-option"))
        self.filesizeprivacyDontSendOption = QRadioButton(getMessage("privacy-dontsend-option"))
        self.filesizeprivacyButtonGroup.addButton(self.filesizeprivacySendRawOption)
        self.filesizeprivacyButtonGroup.addButton(self.filesizeprivacySendHashedOption)
        self.filesizeprivacyButtonGroup.addButton(self.filesizeprivacyDontSendOption)

        self.filenameprivacyLabel.setObjectName("filename-privacy")
        self.filenameprivacySendRawOption.setObjectName("privacy-sendraw" + constants.CONFIG_NAME_MARKER + "filenamePrivacyMode" + constants.CONFIG_VALUE_MARKER + constants.PRIVACY_SENDRAW_MODE)
        self.filenameprivacySendHashedOption.setObjectName("privacy-sendhashed" + constants.CONFIG_NAME_MARKER + "filenamePrivacyMode" + constants.CONFIG_VALUE_MARKER + constants.PRIVACY_SENDHASHED_MODE)
        self.filenameprivacyDontSendOption.setObjectName("privacy-dontsend" + constants.CONFIG_NAME_MARKER + "filenamePrivacyMode" + constants.CONFIG_VALUE_MARKER + constants.PRIVACY_DONTSEND_MODE)
        self.filesizeprivacyLabel.setObjectName("filesize-privacy")
        self.filesizeprivacySendRawOption.setObjectName("privacy-sendraw" + constants.CONFIG_NAME_MARKER + "filesizePrivacyMode" + constants.CONFIG_VALUE_MARKER + constants.PRIVACY_SENDRAW_MODE)
        self.filesizeprivacySendHashedOption.setObjectName("privacy-sendhashed" + constants.CONFIG_NAME_MARKER + "filesizePrivacyMode" + constants.CONFIG_VALUE_MARKER + constants.PRIVACY_SENDHASHED_MODE)
        self.filesizeprivacyDontSendOption.setObjectName("privacy-dontsend" + constants.CONFIG_NAME_MARKER + "filesizePrivacyMode" + constants.CONFIG_VALUE_MARKER + constants.PRIVACY_DONTSEND_MODE)

        self.coreSettingsLayout.addWidget(self.filenameprivacyLabel, 3, 0)
        self.coreSettingsLayout.addWidget(self.filenameprivacySendRawOption, 3, 1, Qt.AlignLeft)
        self.coreSettingsLayout.addWidget(self.filenameprivacySendHashedOption, 3, 2, Qt.AlignLeft)
        self.coreSettingsLayout.addWidget(self.filenameprivacyDontSendOption, 3, 3, Qt.AlignLeft)
        self.coreSettingsLayout.addWidget(self.filesizeprivacyLabel, 4, 0)
        self.coreSettingsLayout.addWidget(self.filesizeprivacySendRawOption, 4, 1, Qt.AlignLeft)
        self.coreSettingsLayout.addWidget(self.filesizeprivacySendHashedOption, 4, 2, Qt.AlignLeft)
        self.coreSettingsLayout.addWidget(self.filesizeprivacyDontSendOption, 4, 3, Qt.AlignLeft)

        ## Syncplay internals

        self.internalSettingsGroup = QtGui.QGroupBox(getMessage("syncplay-internals-title"))
        self.internalSettingsLayout = QtGui.QVBoxLayout()
        self.internalSettingsGroup.setLayout(self.internalSettingsLayout)

        self.alwaysshowCheckbox = QCheckBox(getMessage("forceguiprompt-label"))
        self.alwaysshowCheckbox.setObjectName(constants.INVERTED_STATE_MARKER + "forceGuiPrompt")
        self.internalSettingsLayout.addWidget(self.alwaysshowCheckbox)

        self.automaticupdatesCheckbox = QCheckBox(getMessage("checkforupdatesautomatically-label"))
        self.automaticupdatesCheckbox.setObjectName("checkForUpdatesAutomatically")
        self.internalSettingsLayout.addWidget(self.automaticupdatesCheckbox)

        self.miscLayout.addWidget(self.coreSettingsGroup)
        self.miscLayout.addWidget(self.internalSettingsGroup)
        self.miscLayout.setAlignment(Qt.AlignTop)
        self.stackedLayout.addWidget(self.miscFrame)

    def addSyncTab(self):
        self.syncSettingsFrame = QtGui.QFrame()
        self.syncSettingsLayout = QtGui.QVBoxLayout()

        self.desyncSettingsGroup = QtGui.QGroupBox(getMessage("sync-otherslagging-title"))
        self.desyncOptionsFrame = QtGui.QFrame()
        self.desyncSettingsOptionsLayout = QtGui.QHBoxLayout()
        config = self.config

        self.slowdownCheckbox = QCheckBox(getMessage("slowondesync-label"))
        self.slowdownCheckbox.setObjectName("slowOnDesync")
        self.rewindCheckbox = QCheckBox(getMessage("rewindondesync-label"))
        self.rewindCheckbox.setObjectName("rewindOnDesync")
        self.fastforwardCheckbox = QCheckBox(getMessage("fastforwardondesync-label"))
        self.fastforwardCheckbox.setObjectName("fastforwardOnDesync")

        self.spaceLabel = QLabel()
        self.spaceLabel.setFixedHeight(5)

        self.desyncSettingsLayout = QtGui.QGridLayout()
        self.desyncSettingsLayout.setSpacing(2)
        self.desyncFrame = QtGui.QFrame()
        self.desyncFrame.setLineWidth(0)
        self.desyncFrame.setMidLineWidth(0)

        self.slowdownThresholdLabel = QLabel(getMessage("slowdown-threshold-label"), self)
        self.slowdownThresholdLabel.setStyleSheet(constants.STYLE_SUBLABEL.format(self.posixresourcespath + "chevrons_right.png"))

        self.slowdownThresholdSpinbox = QDoubleSpinBox()
        try:
            slowdownThreshold = float(config['slowdownThreshold'])
            self.slowdownThresholdSpinbox.setValue(slowdownThreshold)
            if slowdownThreshold < constants.MINIMUM_SLOWDOWN_THRESHOLD:
                constants.MINIMUM_SLOWDOWN_THRESHOLD = slowdownThreshold
        except ValueError:
            self.slowdownThresholdSpinbox.setValue(constants.DEFAULT_SLOWDOWN_KICKIN_THRESHOLD)
        self.slowdownThresholdSpinbox.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)
        self.slowdownThresholdSpinbox.setMinimum(constants.MINIMUM_SLOWDOWN_THRESHOLD)
        self.slowdownThresholdSpinbox.setSingleStep(0.1)
        self.slowdownThresholdSpinbox.setSuffix(getMessage("seconds-suffix"))
        self.slowdownThresholdSpinbox.adjustSize()

        self.rewindThresholdLabel = QLabel(getMessage("rewind-threshold-label"), self)
        self.rewindThresholdLabel.setStyleSheet(constants.STYLE_SUBLABEL.format(self.posixresourcespath + "chevrons_right.png"))
        self.rewindThresholdSpinbox = QDoubleSpinBox()
        try:
            rewindThreshold = float(config['rewindThreshold'])
            self.rewindThresholdSpinbox.setValue(rewindThreshold)
            if rewindThreshold < constants.MINIMUM_REWIND_THRESHOLD:
                constants.MINIMUM_REWIND_THRESHOLD = rewindThreshold
        except ValueError:
            self.rewindThresholdSpinbox.setValue(constants.DEFAULT_REWIND_THRESHOLD)
        self.rewindThresholdSpinbox.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)
        self.rewindThresholdSpinbox.setMinimum(constants.MINIMUM_REWIND_THRESHOLD)
        self.rewindThresholdSpinbox.setSingleStep(0.1)
        self.rewindThresholdSpinbox.setSuffix(getMessage("seconds-suffix"))
        self.rewindThresholdSpinbox.adjustSize()

        self.fastforwardThresholdLabel = QLabel(getMessage("fastforward-threshold-label"), self)
        self.fastforwardThresholdLabel.setStyleSheet(constants.STYLE_SUBLABEL.format(self.posixresourcespath + "chevrons_right.png"))
        self.fastforwardThresholdSpinbox = QDoubleSpinBox()
        try:
            fastforwardThreshold = float(config['fastforwardThreshold'])
            self.fastforwardThresholdSpinbox.setValue(fastforwardThreshold)
            if fastforwardThreshold < constants.MINIMUM_FASTFORWARD_THRESHOLD:
                constants.MINIMUM_FASTFORWARD_THRESHOLD = fastforwardThreshold
        except ValueError:
            self.fastforwardThresholdSpinbox.setValue(constants.DEFAULT_FASTFORWARD_THRESHOLD)
        self.fastforwardThresholdSpinbox.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)
        self.fastforwardThresholdSpinbox.setMinimum(constants.MINIMUM_FASTFORWARD_THRESHOLD)
        self.fastforwardThresholdSpinbox.setSingleStep(0.1)
        self.fastforwardThresholdSpinbox.setSuffix(getMessage("seconds-suffix"))
        self.fastforwardThresholdSpinbox.adjustSize()

        self.slowdownThresholdLabel.setObjectName("slowdown-threshold")
        self.slowdownThresholdSpinbox.setObjectName("slowdown-threshold")
        self.rewindThresholdLabel.setObjectName("rewind-threshold")
        self.rewindThresholdSpinbox.setObjectName("rewind-threshold")

        self.desyncSettingsLayout.addWidget(self.slowdownCheckbox, 0, 0, 1, 2, Qt.AlignLeft)
        self.desyncSettingsLayout.addWidget(self.slowdownThresholdLabel, 1, 0, 1, 1, Qt.AlignLeft)
        self.desyncSettingsLayout.addWidget(self.slowdownThresholdSpinbox, 1, 1, 1, 1, Qt.AlignLeft)
        self.desyncSettingsLayout.addWidget(self.spaceLabel, 2, 0,1,2, Qt.AlignLeft)
        self.desyncSettingsLayout.addWidget(self.rewindCheckbox, 3, 0,1,2, Qt.AlignLeft)
        self.desyncSettingsLayout.addWidget(self.rewindThresholdLabel, 4, 0, 1, 1, Qt.AlignLeft)
        self.desyncSettingsLayout.addWidget(self.rewindThresholdSpinbox, 4, 1, Qt.AlignLeft)

        self.subitems['slowOnDesync'] = ["slowdown-threshold"]
        self.subitems['rewindOnDesync'] = ["rewind-threshold"]

        self.desyncSettingsLayout.setAlignment(Qt.AlignLeft)
        self.desyncSettingsGroup.setLayout(self.desyncSettingsLayout)
        self.desyncSettingsOptionsLayout.addWidget(self.desyncFrame)

        self.desyncFrame.setLayout(self.syncSettingsLayout)

        self.othersyncSettingsGroup = QtGui.QGroupBox(getMessage("sync-youlaggging-title"))
        self.othersyncOptionsFrame = QtGui.QFrame()
        self.othersyncSettingsLayout = QtGui.QGridLayout()

        self.dontslowwithmeCheckbox = QCheckBox(getMessage("dontslowdownwithme-label"))
        self.dontslowwithmeCheckbox.setObjectName("dontSlowDownWithMe")

        self.othersyncSettingsLayout.addWidget(self.dontslowwithmeCheckbox, 3, 0, 1, 2, Qt.AlignLeft)

        self.fastforwardThresholdLabel.setObjectName("fastforward-threshold")
        self.fastforwardThresholdSpinbox.setObjectName("fastforward-threshold")

        self.othersyncSettingsLayout.setAlignment(Qt.AlignLeft)
        self.othersyncSettingsLayout.addWidget(self.fastforwardCheckbox, 4, 0,1,2, Qt.AlignLeft)
        self.othersyncSettingsLayout.addWidget(self.fastforwardThresholdLabel, 5, 0, 1, 1, Qt.AlignLeft)
        self.othersyncSettingsLayout.addWidget(self.fastforwardThresholdSpinbox, 5, 1, Qt.AlignLeft)
        self.subitems['fastforwardOnDesync'] = ["fastforward-threshold"]

        self.othersyncSettingsGroup.setLayout(self.othersyncSettingsLayout)
        self.othersyncSettingsGroup.setMaximumHeight(self.othersyncSettingsGroup.minimumSizeHint().height())
        self.syncSettingsLayout.addWidget(self.othersyncSettingsGroup)
        self.syncSettingsLayout.addWidget(self.desyncSettingsGroup)
        self.syncSettingsFrame.setLayout(self.syncSettingsLayout)
        self.desyncSettingsGroup.setMaximumHeight(self.desyncSettingsGroup.minimumSizeHint().height())
        self.syncSettingsLayout.setAlignment(Qt.AlignTop)
        self.stackedLayout.addWidget(self.syncSettingsFrame)

    def addMessageTab(self):
        self.messageFrame = QtGui.QFrame()
        self.messageLayout = QtGui.QVBoxLayout()
        self.messageLayout.setAlignment(Qt.AlignTop)

        # OSD
        self.osdSettingsGroup = QtGui.QGroupBox(getMessage("messages-osd-title"))
        self.osdSettingsLayout = QtGui.QVBoxLayout()
        self.osdSettingsFrame = QtGui.QFrame()

        self.showOSDCheckbox = QCheckBox(getMessage("showosd-label"))
        self.showOSDCheckbox.setObjectName("showOSD")
        self.osdSettingsLayout.addWidget(self.showOSDCheckbox)

        self.showSameRoomOSDCheckbox = QCheckBox(getMessage("showsameroomosd-label"))
        self.showSameRoomOSDCheckbox.setObjectName("showSameRoomOSD")
        self.showSameRoomOSDCheckbox.setStyleSheet(constants.STYLE_SUBCHECKBOX.format(self.posixresourcespath + "chevrons_right.png"))
        self.osdSettingsLayout.addWidget(self.showSameRoomOSDCheckbox)

        self.showNonControllerOSDCheckbox = QCheckBox(getMessage("shownoncontrollerosd-label"))
        self.showNonControllerOSDCheckbox.setObjectName("showNonControllerOSD")
        self.showNonControllerOSDCheckbox.setStyleSheet(constants.STYLE_SUBCHECKBOX.format(self.posixresourcespath + "chevrons_right.png"))
        self.osdSettingsLayout.addWidget(self.showNonControllerOSDCheckbox)

        self.showDifferentRoomOSDCheckbox = QCheckBox(getMessage("showdifferentroomosd-label"))
        self.showDifferentRoomOSDCheckbox.setObjectName("showDifferentRoomOSD")
        self.showDifferentRoomOSDCheckbox.setStyleSheet(constants.STYLE_SUBCHECKBOX.format(self.posixresourcespath + "chevrons_right.png"))
        self.osdSettingsLayout.addWidget(self.showDifferentRoomOSDCheckbox)

        self.slowdownOSDCheckbox = QCheckBox(getMessage("showslowdownosd-label"))
        self.slowdownOSDCheckbox.setObjectName("showSlowdownOSD")
        self.slowdownOSDCheckbox.setStyleSheet(constants.STYLE_SUBCHECKBOX.format(self.posixresourcespath + "chevrons_right.png"))
        self.osdSettingsLayout.addWidget(self.slowdownOSDCheckbox)

        self.showOSDWarningsCheckbox = QCheckBox(getMessage("showosdwarnings-label"))
        self.showOSDWarningsCheckbox.setObjectName("showOSDWarnings")
        self.showOSDWarningsCheckbox.setStyleSheet(constants.STYLE_SUBCHECKBOX.format(self.posixresourcespath + "chevrons_right.png"))
        self.osdSettingsLayout.addWidget(self.showOSDWarningsCheckbox)

        self.subitems['showOSD'] = ["showSameRoomOSD", "showDifferentRoomOSD", "showSlowdownOSD", "showOSDWarnings", "showNonControllerOSD"]

        self.osdSettingsGroup.setLayout(self.osdSettingsLayout)
        self.osdSettingsGroup.setMaximumHeight(self.osdSettingsGroup.minimumSizeHint().height())
        self.osdSettingsLayout.setAlignment(Qt.AlignTop)
        self.messageLayout.addWidget(self.osdSettingsGroup)

        # Other display

        self.displaySettingsGroup = QtGui.QGroupBox(getMessage("messages-other-title"))
        self.displaySettingsLayout = QtGui.QVBoxLayout()
        self.displaySettingsLayout.setAlignment(Qt.AlignTop & Qt.AlignLeft)
        self.displaySettingsFrame = QtGui.QFrame()

        self.showDurationNotificationCheckbox = QCheckBox(getMessage("showdurationnotification-label"))
        self.showDurationNotificationCheckbox.setObjectName("showDurationNotification")
        self.displaySettingsLayout.addWidget(self.showDurationNotificationCheckbox)

        self.languageFrame = QtGui.QFrame()
        self.languageLayout = QtGui.QHBoxLayout()
        self.languageLayout.setContentsMargins(0, 0, 0, 0)
        self.languageFrame.setLayout(self.languageLayout)
        self.languageFrame.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)
        self.languageLayout.setAlignment(Qt.AlignTop & Qt.AlignLeft)
        self.languageLabel = QLabel(getMessage("language-label"), self)
        self.languageCombobox = QtGui.QComboBox(self)
        self.languageCombobox.addItem(getMessage("automatic-language").format(getMessage("LANGUAGE", getInitialLanguage())))

        self.languages = getLanguages()
        for lang in self.languages:
            self.languageCombobox.addItem(self.languages[lang], lang)
            if lang == self.config['language']:
                self.languageCombobox.setCurrentIndex(self.languageCombobox.count()-1)
        self.languageCombobox.currentIndexChanged.connect(self.languageChanged)
        self.languageLayout.addWidget(self.languageLabel, 1, 0)
        self.languageLayout.addWidget(self.languageCombobox, 1, 1)
        self.displaySettingsLayout.addWidget(self.languageFrame)

        self.languageLabel.setObjectName("language")
        self.languageCombobox.setObjectName("language")
        self.languageFrame.setMaximumWidth(self.languageFrame.minimumSizeHint().width())

        self.displaySettingsGroup.setLayout(self.displaySettingsLayout)
        self.displaySettingsGroup.setMaximumHeight(self.displaySettingsGroup.minimumSizeHint().height())
        self.displaySettingsLayout.setAlignment(Qt.AlignTop & Qt.AlignLeft)
        self.messageLayout.addWidget(self.displaySettingsGroup)

        # messageFrame
        self.messageFrame.setLayout(self.messageLayout)
        self.stackedLayout.addWidget(self.messageFrame)

    def addBottomLayout(self):
        config = self.config
        resourcespath = self.resourcespath

        self.bottomButtonFrame = QtGui.QFrame()
        self.bottomButtonLayout = QtGui.QHBoxLayout()
        self.helpButton = QtGui.QPushButton(QtGui.QIcon(self.resourcespath + 'help.png'), getMessage("help-label"))
        self.helpButton.setObjectName("help")
        self.helpButton.setMaximumSize(self.helpButton.sizeHint())
        self.helpButton.pressed.connect(self.openHelp)

        self.resetButton = QtGui.QPushButton(QtGui.QIcon(resourcespath + 'cog_delete.png'),getMessage("reset-label"))
        self.resetButton.setMaximumSize(self.resetButton.sizeHint())
        self.resetButton.setObjectName("reset")
        self.resetButton.pressed.connect(self.resetSettings)

        self.runButton = QtGui.QPushButton(QtGui.QIcon(resourcespath + 'accept.png'), getMessage("storeandrun-label"))
        self.runButton.pressed.connect(self._saveDataAndLeave)
        self.bottomButtonLayout.addWidget(self.helpButton)
        self.bottomButtonLayout.addWidget(self.resetButton)
        self.bottomButtonLayout.addWidget(self.runButton)
        self.bottomButtonFrame.setLayout(self.bottomButtonLayout)
        if config['noStore'] == True:
            self.runButton.setText(getMessage("run-label"))
        self.bottomButtonLayout.setContentsMargins(5,0,5,0)
        self.mainLayout.addWidget(self.bottomButtonFrame, 1, 0, 1, 2)

        self.bottomCheckboxFrame = QtGui.QFrame()
        self.bottomCheckboxFrame.setContentsMargins(0,0,0,0)
        self.bottomCheckboxLayout = QtGui.QGridLayout()
        self.alwaysshowCheckbox = QCheckBox(getMessage("forceguiprompt-label"))

        self.nostoreCheckbox = QCheckBox(getMessage("nostore-label"))
        self.bottomCheckboxLayout.addWidget(self.showmoreCheckbox)
        self.bottomCheckboxLayout.addWidget(self.nostoreCheckbox, 0, 2, Qt.AlignRight)
        self.alwaysshowCheckbox.setObjectName(constants.INVERTED_STATE_MARKER + "forceGuiPrompt")
        self.nostoreCheckbox.setObjectName("noStore")
        self.nostoreCheckbox.toggled.connect(self.runButtonTextUpdate)
        self.bottomCheckboxFrame.setLayout(self.bottomCheckboxLayout)

        self.mainLayout.addWidget(self.bottomCheckboxFrame, 2, 0, 1, 2)

    def tabList(self):
        self.tabListLayout = QtGui.QHBoxLayout()
        self.tabListFrame = QtGui.QFrame()
        self.tabListWidget = QtGui.QListWidget()
        self.tabListWidget.addItem(QtGui.QListWidgetItem(QtGui.QIcon(self.resourcespath + "house.png"),getMessage("basics-label")))
        self.tabListWidget.addItem(QtGui.QListWidgetItem(QtGui.QIcon(self.resourcespath + "cog.png"),getMessage("misc-label")))
        self.tabListWidget.addItem(QtGui.QListWidgetItem(QtGui.QIcon(self.resourcespath + "film_link.png"),getMessage("sync-label")))
        self.tabListWidget.addItem(QtGui.QListWidgetItem(QtGui.QIcon(self.resourcespath + "comments.png"),getMessage("messages-label")))
        self.tabListLayout.addWidget(self.tabListWidget)
        self.tabListFrame.setLayout(self.tabListLayout)
        self.tabListFrame.setFixedWidth(self.tabListFrame.minimumSizeHint().width())
        self.tabListWidget.setStyleSheet(constants.STYLE_TABLIST)

        self.tabListWidget.currentItemChanged.connect(self.tabChange)
        self.tabListWidget.itemClicked.connect(self.tabChange)
        self.tabListWidget.itemPressed.connect(self.tabChange)
        self.mainLayout.addWidget(self.tabListFrame, 0, 0, 1, 1)

    def ensureTabListIsVisible(self):
        self.stackedFrame.setFixedWidth(self.stackedFrame.width())
        while self.tabListWidget.horizontalScrollBar().isVisible() and self.tabListFrame.width() < 200:
            self.tabListFrame.setFixedWidth(self.tabListFrame.width()+1)

    def tabChange(self):
        self.setFocus()
        self.stackedLayout.setCurrentIndex(self.tabListWidget.currentRow())

    def resetSettings(self):
        self.clearGUIData(leaveMore=True)
        self.config['resetConfig'] = True
        self.pressedclosebutton = True
        self.close()

    def showEvent(self, *args, **kwargs):
        self.ensureTabListIsVisible()
        self.setFixedWidth(self.minimumSizeHint().width())
        self.executablepathCombobox.setFixedWidth(self.mediapathTextbox.width())

    def clearGUIData(self, leaveMore=False):
        settings = QSettings("Syncplay", "PlayerList")
        settings.clear()
        settings = QSettings("Syncplay", "MediaBrowseDialog")
        settings.clear()
        settings = QSettings("Syncplay", "MainWindow")
        settings.clear()
        settings = QSettings("Syncplay", "Interface")
        settings.beginGroup("Update")
        settings.setValue("lastChecked", None)
        settings.endGroup()
        if not leaveMore:
            settings = QSettings("Syncplay", "MoreSettings")
            settings.clear()
        self.datacleared = True

    def __init__(self, config, playerpaths, error, defaultConfig):

        from syncplay import utils
        self.config = config
        self.defaultConfig = defaultConfig
        self.playerpaths = playerpaths
        self.datacleared = False
        self.config['resetConfig'] = False
        self.subitems = {}

        if self.config['clearGUIData'] == True:
            self.config['clearGUIData'] = False
            self.clearGUIData()

        self.QtGui = QtGui
        self.error = error
        if sys.platform.startswith('win'):
            resourcespath = utils.findWorkingDir() + "\\resources\\"
        else:
            resourcespath = utils.findWorkingDir() + "/resources/"
        self.posixresourcespath = utils.findWorkingDir().replace("\\","/") + "/resources/"
        self.resourcespath = resourcespath

        super(ConfigDialog, self).__init__()

        self.setWindowTitle(getMessage("config-window-title"))
        self.setWindowFlags(self.windowFlags() & Qt.WindowCloseButtonHint & ~Qt.WindowContextHelpButtonHint)
        self.setWindowIcon(QtGui.QIcon(resourcespath + "syncplay.png"))

        self.stackedLayout = QtGui.QStackedLayout()
        self.stackedFrame = QtGui.QFrame()
        self.stackedFrame.setLayout(self.stackedLayout)

        self.mainLayout = QtGui.QGridLayout()
        self.mainLayout.setSpacing(0)
        self.mainLayout.setContentsMargins(0,0,0,0)

        self.addBasicTab()
        self.addMiscTab()
        self.addSyncTab()
        self.addMessageTab()
        self.tabList()

        self.mainLayout.addWidget(self.stackedFrame, 0, 1)
        self.addBottomLayout()


        if self.getMoreState() == False:
            self.tabListFrame.hide()
            self.nostoreCheckbox.hide()
            self.resetButton.hide()
        else:
            self.showmoreCheckbox.setChecked(True)
            self.tabListWidget.setCurrentRow(0)

        self.showmoreCheckbox.toggled.connect(self.moreToggled)

        self.setLayout(self.mainLayout)
        self.runButton.setFocus()
        self.setFixedSize(self.sizeHint())
        self.setAcceptDrops(True)

        if constants.SHOW_TOOLTIPS:
            self.processWidget(self, lambda w: self.loadTooltips(w))
        self.processWidget(self, lambda w: self.loadValues(w))
        self.processWidget(self, lambda w: self.connectChildren(w))