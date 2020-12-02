import binascii
import configparser
import sys
from enum import Enum

import serial
import serial.tools.list_ports
from PyQt5.QtWidgets import (QApplication, QComboBox, QMainWindow, QMessageBox,
                             QWidget, QRadioButton, QCheckBox, QSpinBox, QTextEdit, QLineEdit)

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
        self.openComPortBtn.clicked.connect(self.OpenComPort)
        self.refreshComPorts.clicked.connect(self.GetSysComPortListsFillInComboBox)

    # 按指定配置打开串口
    def OpenComPort(self):
        if self.openComPortBtn.text() == "打开串口":
            self.ser = serial.Serial()
            self.ser.port = self.COM_PORTS.currentText()
            self.ser.baudrate = int(self.BAUDRATES.currentText())
            self.ser.parity = eval("serial.PARITY_" + self.VERIFY_BITS.currentText())
            stopbitsDic = {1: "ONE", 1.5: "ONE_POINT_FIVE", 2:"TWO"}
            self.ser.stopbits = eval("serial.STOPBITS_" + stopbitsDic[float(self.STOP_BITS.currentText())])
            bytesizeDic = {5:"FIVEBITS", 6:"SIXBITS", 7:"SEVENBITS", 8:"EIGHTBITS"}
            self.ser.bytesize = eval("serial." + bytesizeDic[int(self.DATA_BITS.currentText())])
            isSoftControl = True if "XON/XOFF" in self.FLOW_CONTROLS.currentText() else False
            isRTSCTSControl = True if "RTS/CTS" in self.FLOW_CONTROLS.currentText() else False
            isDSRDTRControl = True if "DTR/DSR" in self.FLOW_CONTROLS.currentText() else False
            if isSoftControl: self.ser.xonxoff = True
            if isRTSCTSControl: self.ser.rtscts = True
            if isDSRDTRControl: self.ser.dsrdtr = True
            try:
                self.ser.open()
                self.openComPortBtn.setText("关闭串口")
                self.COM_PORTS.setEnabled(False)
            except(OSError):
                QMessageBox.information(self, '串口打开错误', '请检查串口设定', QMessageBox.Ok, QMessageBox.Ok)
        else:
            self.ser.close()
            self.openComPortBtn.setText("打开串口")
            self.COM_PORTS.setEnabled(True)

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
                    obj.clicked.connect(self.WriteReiceiveSettingsToIni)

    # 将串口接收设定写入配置文件

    def WriteReiceiveSettingsToIni(self):
        para = self.sender().objectName()
        cfgValue = ""
        if isinstance(self.sender(), QRadioButton):
            cfgValue = "ASCII" if self.RCV_MODE_ASCII.isChecked() else "HEX"
            para = "RCV_MODE"
        if isinstance(self.sender(), QCheckBox):
            cfgValue = "YES" if self.sender().isChecked() else "NO"
        self.cfgParser.WriteINISectionValues(cfgValue, "RECEIVE", para)

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
                        obj.clicked.connect(self.WriteDataFrameSettingsToIni)
                    if isinstance(obj, QCheckBox):
                        iniSectionValue = self.cfgParser.GetINISectionContents(
                            None, "DATA_FRAME", obj.objectName())
                        if iniSectionValue != "NO":
                            obj.setChecked(True)
                        obj.clicked.connect(self.WriteDataFrameSettingsToIni)
                    if isinstance(obj, QLineEdit):
                        iniSectionValue = self.cfgParser.GetINISectionContents(None, "DATA_FRAME", obj.objectName())
                        obj.setText(iniSectionValue)
                        obj.textChanged.connect(self.WriteDataFrameSettingsToIni)
                    if isinstance(obj, QSpinBox):
                        iniSectionValue = self.cfgParser.GetINISectionContents(
                            None, "DATA_FRAME", obj.objectName())
                        obj.setValue(int(iniSectionValue))
                        obj.valueChanged.connect(
                            self.WriteDataFrameSettingsToIni)

    # 将数据帧设定写入配置文件
    def WriteDataFrameSettingsToIni(self):
        para = self.sender().objectName()
        cfgValue = ""
        if isinstance(self.sender(), QRadioButton):
            cfgValue = "FIXED" if self.DF_LENGTH_MODE_FIXED.isChecked() else "VARIABLE"
            para = "DF_LENGTH_MODE"
        if isinstance(self.sender(), QCheckBox):
            cfgValue = "YES" if self.sender().isChecked() else "NO"
        if isinstance(self.sender(), QSpinBox):
            cfgValue = str(self.sender().value())
        if isinstance(self.sender(), QLineEdit):
            cfgValue = self.sender().text()
        # print(cfgValue + " |DATA_FRAME|", para)
        self.cfgParser.WriteINISectionValues(cfgValue, "DATA_FRAME", para)

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
            # print(cmd)
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
