import binascii
import configparser
import sys
import threading
import time
from datetime import datetime
from enum import Enum
import regex as re

import serial
import serial.tools.list_ports
from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QLineEdit,
                             QMainWindow, QMessageBox, QRadioButton, QSpinBox,
                             QTextEdit, QWidget)

import Ui_main as mainForm

isReading = True
uncompletedString = ""
dt_frame_start = ""
dt_frame_end = ""
rcvHexFormat = True

# 主窗口包装类


class MyMainWindow(QMainWindow, mainForm.Ui_MainWindow):
    def __init__(self, parent=None):
        global rcvHexFormat
        super(MyMainWindow, self).__init__(parent)
        self.setupUi(self)
        self.cfgParser = INIParser("config.ini")
        self.FillItemsInComboBoxes()
        self.GetSysComPortListsFillInComboBox()
        self.GetReiceiveSettingsFromIni()
        if not self.RCV_CUT_FORMAT.isChecked():
            self.RCV_DISPLAY_FORMAT.setEnabled(False)
        if not self.RCV_MODE_HEX.isChecked():
            rcvHexFormat = False
        self.GetSendSettingsFromIni()
        self.GetDataFrameSettingsFromIni()
        self.openComPortBtn.clicked.connect(self.OpenComPort)
        self.refreshComPorts.clicked.connect(
            self.GetSysComPortListsFillInComboBox)

    # 按指定配置打开串口
    def OpenComPort(self):
        global isReading
        if self.openComPortBtn.text() == "打开串口":
            self.ser = serial.Serial()
            self.ser.port = self.COM_PORTS.currentText()
            self.ser.baudrate = int(self.BAUDRATES.currentText())
            self.ser.parity = eval(
                "serial.PARITY_" + self.VERIFY_BITS.currentText())
            stopbitsDic = {1: "ONE", 1.5: "ONE_POINT_FIVE", 2: "TWO"}
            self.ser.stopbits = eval(
                "serial.STOPBITS_" + stopbitsDic[float(self.STOP_BITS.currentText())])
            bytesizeDic = {5: "FIVEBITS", 6: "SIXBITS",
                           7: "SEVENBITS", 8: "EIGHTBITS"}
            self.ser.bytesize = eval(
                "serial." + bytesizeDic[int(self.DATA_BITS.currentText())])
            self.ser.xonxoff = True if "XON" in self.FLOW_CONTROLS.currentText() else False
            self.ser.rtscts = True if "RTS" in self.FLOW_CONTROLS.currentText() else False
            self.ser.dsrdtr = True if "DTR" in self.FLOW_CONTROLS.currentText() else False
            try:
                self.ser.open()
                self.openComPortBtn.setText("关闭串口")
                self.SetComSettingControlsEnabled(False)
                self.openedComPortDetail = "{0}   波特率：{1}   数据位：{2}   停止位：{3}   XON/XOFF：{4}   DTS/RTS：{5}   DSR/DTR: {6}".format(
                    self.ser.name, self.ser.baudrate, self.ser.bytesize, self.ser.stopbits, "打开" if self.ser.xonxoff else "关闭",
                    "打开" if self.ser.rtscts else "关闭", "打开" if self.ser.dsrdtr else "关闭")
                self.statusBar().showMessage("已打开：" + self.openedComPortDetail)
                isReading = True
                self.readThread = ReadThread(self.ser)
                self.readThread.trigger.connect(self.GetReadMsgToTextEdit)
                self.readThread.start()
            except Exception as e:
                QMessageBox.information(
                    self, '串口打开错误', '错误信息：{0}，请检查串口设定'.format(str(e)), QMessageBox.Ok, QMessageBox.Ok)
        else:
            isReading = False
            time.sleep(0.1)
            # self.readThread.quit()
            # self.readThread = None
            self.ser.close()
            self.openComPortBtn.setText("打开串口")
            self.statusBar().showMessage("已关闭：" + self.ser.name)
            self.SetComSettingControlsEnabled(True)

    # 串口接收到的信息追加至 logTextEdit
    def GetReadMsgToTextEdit(self, msg):
        global uncompletedString, dt_frame_start, dt_frame_end
        displayDtFormat = self.RCV_DISPLAY_FORMAT.isChecked()
        currentText = self.logTextEdit.toPlainText()
        needChangeLine = "" if currentText == "" else "\n"
        textColorFormat = "<span style=\" font-size:10pt; color:#0000ff;\" >"
        formatEnd = "</span>"
        if self.RCV_CUT_FORMAT.isChecked():
            if uncompletedString != "":
                msg = uncompletedString + " " + msg
                uncompletedString = ""
            firstArr = msg.split(dt_frame_start)
            if len(firstArr) > 0:
                for arr in firstArr:
                    if dt_frame_end in arr:
                        self.logTextEdit.append("{0}{1}{2}  RXD:  {3} {4} {5}{6}".format(
                            textColorFormat, needChangeLine, datetime.now().strftime("%H:%M:%S"), dt_frame_start if displayDtFormat else "", arr.split(dt_frame_end)[0].strip(), dt_frame_end if displayDtFormat else "", formatEnd))
                        self.logTextEdit.moveCursor(QtGui.QTextCursor.End)
                    else:
                        uncompletedString += arr
        else:
            self.logTextEdit.append("{0}{1}{2}  RXD:  {3}{4}".format(
                textColorFormat, needChangeLine, datetime.now().strftime("%H:%M:%S"), msg, formatEnd))

    def SetComSettingControlsEnabled(self, enable):
        self.COM_PORTS.setEnabled(enable)
        self.BAUDRATES.setEnabled(enable)
        self.VERIFY_BITS.setEnabled(enable)
        self.DATA_BITS.setEnabled(enable)
        self.STOP_BITS.setEnabled(enable)
        self.FLOW_CONTROLS.setEnabled(enable)
        self.refreshComPorts.setEnabled(enable)

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
        global rcvHexFormat
        para = self.sender().objectName()
        cfgValue = ""
        if isinstance(self.sender(), QRadioButton):
            cfgValue = "ASCII" if self.RCV_MODE_ASCII.isChecked() else "HEX"
            para = "RCV_MODE"
            rcvHexFormat = True if self.RCV_MODE_HEX.isChecked() else False
        if isinstance(self.sender(), QCheckBox):
            cfgValue = "YES" if self.sender().isChecked() else "NO"
        if self.sender().objectName() == "RCV_CUT_FORMAT":
            if self.sender().isChecked():
                self.RCV_DISPLAY_FORMAT.setEnabled(True)
            else:
                self.RCV_DISPLAY_FORMAT.setEnabled(False)
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
        global dt_frame_start, dt_frame_end
        dt_frame_start = self.cfgParser.GetINISectionContents(
            None, "DATA_FRAME", "DF_START_BIT")
        dt_frame_end = self.cfgParser.GetINISectionContents(
            None, "DATA_FRAME", "DF_END_BIT")
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
                        iniSectionValue = self.cfgParser.GetINISectionContents(
                            None, "DATA_FRAME", obj.objectName())
                        obj.setText(iniSectionValue)
                        obj.textChanged.connect(
                            self.WriteDataFrameSettingsToIni)
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


class ReadThread(QtCore.QThread):
    # 自定义信号，用来触发串口读取信息到 textedit
    trigger = QtCore.pyqtSignal(str)

    def __init__(self, comPort):
        super(ReadThread, self).__init__()
        self.comPort = comPort

    def run(self):
        global isReading,rcvHexFormat
        over_time = 30
        start_time = time.time()
        while isReading:
            time.sleep(0.1)
            end_time = time.time()
            if end_time - start_time < over_time:
                start_time = time.time()
                if self.comPort.inWaiting() > 0:
                    if rcvHexFormat:
                        msg = ' '.join(
                            ['%02x' % b for b in self.comPort.read_all()])
                        self.trigger.emit(msg.upper())
                    else:
                        # msg = "".join(str(type(self.comPort.read_all())))
                        originMsg = self.comPort.read_all()
                        try:
                            msg =str(originMsg, encoding='gbk')
                        except:
                            msg = str(originMsg)
                        self.trigger.emit(msg)


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
    RCV_DISPLAY_FORMAT = "displaydataframeformat"

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
