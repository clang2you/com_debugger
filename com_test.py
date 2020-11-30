import binascii
import configparser
import sys
from enum import Enum

import serial
import serial.tools.list_ports
from PyQt5.QtWidgets import (QApplication, QComboBox, QMainWindow, QMessageBox,
                             QWidget, QRadioButton, QCheckBox, QSpinBox)

import Ui_main as mainForm


# 主窗口包装类
class MyMainWindow(QMainWindow, mainForm.Ui_MainWindow):
    def __init__(self, parent=None):
        super(MyMainWindow, self).__init__(parent)
        self.setupUi(self)
        self.cfgParser = INIParser("config.ini")
        self.FillItemsInComboBoxes()
        self.GetSysComPortListsFillInComboBox()
        self.GetReiceiveSettingsFromIni()
        self.GetSendSettingsFromIni()
        self.GetDataFrameSettingsFromIni()

    # 将配置文件中的选项填充到对应的 ComboBox 中
    def FillItemsInComboBoxes(self):
        enumList = []
        for k, v in CfgEnum.__members__.items():
            enumList.append(k)
        for widgetsObjs in self.centralwidget.children():
            for obj in widgetsObjs.children():
                name = obj.objectName()
                if isinstance(obj, QComboBox) and name in enumList:
                    secondKey = ""
                    for k in self.cfgParser.GetINISectionContents(None, name):
                        secondKey = k
                    items = self.cfgParser.GetINISectionContents(
                        secondKey, name).split(';')
                    obj.clear()
                    obj.addItems(items)
                    obj.setCurrentText(self.cfgParser.GetINISectionContents(
                        None,  "BASIC", name[:-1]))
                    obj.currentTextChanged.connect(
                        self.WriteCurrentSettingToIni)

    # 从配置文件读取串口接收设定

    def GetReiceiveSettingsFromIni(self):
        for widgetsObjs in self.centralwidget.children():
            for obj in widgetsObjs.children():
                if "RCV" in obj.objectName():
                    if isinstance(obj, QRadioButton):
                        iniSectionValue = self.cfgParser.GetINISectionContents(
                            None, "RECEIVE", "RCV_MODE")
                        if iniSectionValue in obj.objectName():
                            obj.setChecked(True)
                    if isinstance(obj, QCheckBox):
                        iniSectionValue = self.cfgParser.GetINISectionContents(
                            None, "RECEIVE", obj.objectName())
                        if iniSectionValue != "NO":
                            obj.setChecked(True)

    # 将串口接收设定写入配置文件

    def WriteReiceiveSettingsToIni(self):
        pass

    # 从配置文件读取串口发送设定
    def GetSendSettingsFromIni(self):
        for widgetsObjs in self.centralwidget.children():
            for obj in widgetsObjs.children():
                if "SND" in obj.objectName():
                    if isinstance(obj, QRadioButton):
                        iniSectionValue = self.cfgParser.GetINISectionContents(
                            None, "SEND", "SND_MODE")
                        if iniSectionValue in obj.objectName():
                            obj.setChecked(True)
                        obj.clicked.connect(self.WriteSendSettingsToIni)
                    if isinstance(obj, QCheckBox):
                        iniSectionValue = self.cfgParser.GetINISectionContents(
                            None, "SEND", obj.objectName())
                        if iniSectionValue != "NO":
                            obj.setChecked(True)
                        obj.clicked.connect(self.WriteSendSettingsToIni)
                    if isinstance(obj, QSpinBox):
                        iniSectionValue = self.cfgParser.GetINISectionContents(
                            None, "SEND", obj.objectName())
                        obj.setValue(int(iniSectionValue))
                        obj.valueChanged.connect(self.WriteSendSettingsToIni)

    # 将串口发送设定写入配置文件

    def WriteSendSettingsToIni(self):
        para = self.sender().objectName()
        cfgValue = ""
        if isinstance(self.sender(), QRadioButton):
            cfgValue = "ASCII" if self.SND_MODE_ASCII.isChecked() else "HEX"
            para = "SND_MODE"
        if isinstance(self.sender(), QCheckBox):
            cfgValue = "YES" if self.sender().isChecked() else "NO"
        if isinstance(self.sender(), QSpinBox):
            cfgValue = str(self.sender().value())
        self.cfgParser.WriteINISectionValues(cfgValue, "SEND", para)

    # 从配置文件读取数据帧设定
    def GetDataFrameSettingsFromIni(self):
        for widgetsObjs in self.centralwidget.children():
            for obj in widgetsObjs.children():
                if "DF" in obj.objectName():
                    if isinstance(obj, QRadioButton):
                        iniSectionValue = self.cfgParser.GetINISectionContents(
                            None, "DATA_FRAME", "DF_LENGTH_MODE")
                        if iniSectionValue in obj.objectName():
                            obj.setChecked(True)
                    if isinstance(obj, QCheckBox):
                        iniSectionValue = self.cfgParser.GetINISectionContents(
                            None, "DATA_FRAME", obj.objectName())
                        if iniSectionValue != "NO":
                            obj.setChecked(True)

    # 将数据帧设定写入配置文件
    def WriteDataFrameSettingsToIni(self):
        pass

    # 将系统中的串口列表填入下拉框
    def GetSysComPortListsFillInComboBox(self):
        self.COM_PORTS.clear()
        self.COM_PORTS.addItems(
            [port[0] for port in serial.tools.list_ports.comports() if port[2] != 'n/a'])

    # 将当前配置写入配置文件
    def WriteCurrentSettingToIni(self):
        if isinstance(self.sender(), QComboBox):
            self.cfgParser.WriteINISectionValues(
                self.sender().currentText(), "BASIC", self.sender().objectName()[:-1])

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

    def GetINISectionContents(self, section=None, *args):
        content = ""
        if len(args) > 0:
            listSectionContentsCmd = 'self.config'
            for arg in args:
                listSectionContentsCmd = listSectionContentsCmd + \
                    "[CfgEnum.{0}.value]".format(arg)
            if section:
                listSectionContentsCmd = listSectionContentsCmd + \
                    '["{0}"]'.format(section)
            # print(listSectionContentsCmd)
            content = eval(listSectionContentsCmd)
        return content

    def WriteINISectionValues(self, value, *args):
        if len(args) > 0:
            cmd = 'self.config'
            for arg in args:
                cmd = cmd + "[CfgEnum.{0}.value]".format(arg)
            cmd = cmd + ' = "{0}"'.format(value)
            print(cmd)
            exec(cmd)
            with open(self.iniFile, "w") as configFile:
                self.config.write(configFile)


# config.ini


class CfgEnum(Enum):
    BASIC = "BasicConfig"
    RECEIVE = "ReceiveConfig"
    SEND = "SendConfig"
    DATA_FRAME = "DataFrameConfig"
    BAUDRATES = "Baudrate"
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
    CRC_MODE = "selectedcrcmode"

    # ReceiveConfig
    RCV_MODE = "receivedMode"
    RCV_CHG_LINE = "logAutoChangeLine"
    RCV_OFF_DISPLAY = "messageNoDisplay"
    RCV_SAV_FILE = "messageSaveToFile"
    RCV_CUT_FORMAT = "messageCutByDataFrameFormat"

    # SendConfig
    SND_MODE = "sendMode"
    SND_TRS_TOKEN = "autoTransferToken"
    SND_AUTO_ENTER = "atCmdAutoEnter"
    SND_ATT_BIT = "autoSendAttachBit"
    SND_FORMAT = "sendByDataFrameFormat"
    SND_CIRCLE = "circle"
    SND_CIRCLE_INT = "circleInterval"

    # DataFrameConfig
    DF_LENGTH_MODE = "fixedLength"
    DF_LENGTH = "length"
    DF_START_BIT = "startBit"
    DF_END_BIT = "endBit"
    DF_WITH_CRC = "endWithCrc"


# 程序入口，初始化窗体
if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainWindow = MyMainWindow()
    mainWindow.show()
    sys.exit(app.exec_())
