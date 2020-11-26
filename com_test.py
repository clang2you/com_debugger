import binascii
import configparser
import sys
from enum import Enum

import serial
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QWidget

import Ui_main as mainForm


# 主窗口包装类
class MyMainWindow(QMainWindow, mainForm.Ui_MainWindow):
    def __init__(self, parent=None):
        super(MyMainWindow, self).__init__(parent)
        self.setupUi(self)
        self.cfgParser = INIParser("config.ini")
    
    def FillItemsInComboBoxes(self):
        pass

# 配置文件解析


class INIParser():
    def __init__(self, iniFile):
        self.config = configparser.ConfigParser()
        self.iniFile = iniFile
        self.config.read(self.iniFile)

    def ListINISections(self):
        self.iniSections = self.config.sections()
        return self.iniSections

    def ListKeysInSection(self, section):
        return self.config[section]

    def GetINISectionContents(self, *args):
        content = ""
        if len(args) > 0:
            listSectionContentsCmd = 'self.config'
            for arg in args:
                listSectionContentsCmd = listSectionContentsCmd + \
                    "[CfgEnum.{0}.value]".format(arg)
            content = eval(listSectionContentsCmd)
        return content

    def WriteINISectionValues(self, value, *args):
        if len(args) > 0:
            cmd = 'self.config'
            for arg in args:
                cmd = cmd + "[CfgEnum.{0}.value]".format(arg)
            cmd = cmd + ' = "{0}"'.format(value)
            exec(cmd)
            with open(self.iniFile, "w") as configFile:
                self.config.write(configFile)
    

# config.ini


class CfgEnum(Enum):
    BASIC = "BasicConfig"
    RECEIVE = "ReceiveConfig"
    SEND = "SendConfig"
    DATA_FRAME = "DataFrameConfig"
    BAUDRATES = "Baudarate"
    VERIFY_BITS = "VerifyBit"
    DATA_BITS = "DataBit"
    STOP_BITS = "StopBit"
    FLOW_CONTROLS = "FlowControl"
    CRC_MODES = "CrcMode"

    # BasicConfig
    COM_PORT = "selectedComPort"
    BAUDRATE = "selectedBaudrate"
    VERIFY_BIT = "selectedVerifyBit"
    DATA_BIT = "selectedDataBit"
    STOP_BIT = "selectedStopBit"
    FLOW_CONTROL = "selectedFlowControl"

    # ReceiveConfig
    RCV_MODE = "receivedMode"
    CHG_LINE = "logAutoChangeLine"
    OFF_DISPLAY = "messageNoDisplay"
    SAV_FILE = "messageSaveToFile"
    CUT_FORMAT = "messageCutByDataFrameFormat"

    # SendConfig
    SND_MODE = "sendMode"
    TRS_TOKEN = "autoTransferToken"
    AUTO_ENTER = "atCmdAutoEnter"
    SND_ATT_BIT = "autoSendAttachBit"
    SND_FORMAT = "sendByDataFrameFormat"
    CIRCLE = "circle"
    CIRCLE_INT = "circleInterval"

    # DataFrameConfig
    FIXED_LENGTH = "fixedLength"
    LENGTH = "length"
    START_BIT = "startBit"
    END_BIT = "endBit"
    WITH_CRC = "endWithCrc"
    CRC_MODE = "crcMode"


# 程序入口，初始化窗体
if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainWindow = MyMainWindow()
    mainWindow.show()
    sys.exit(app.exec_())
