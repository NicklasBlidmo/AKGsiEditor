'''
coordinate_editor -- shortdesc

coordinate_editor is a description

It defines classes_and_methods

@author:     user_name

@copyright:  2018 organization_name. All rights reserved.

@license:    license

@contact:    user_email
@deffield    updated: Updated
'''

# GSI 16 word format
#*110001+000RTCM-Ref 0454 81...6+0000006742974308 82...6+0000065558922759 83...6+0000000000436354 72....+0000000000000000 73....+0000000000000000 74....+0000000000000000 75....+0000000000000000 
#*110002+0000000000020363 81...6+0000006774180503 82...6+0000065560868658 83...6+0000000000256145 72....+0000000000002022 73....+00000000000000KN 74....+0000000000000001 75....+0000000000000000 


import sys
import os.path
from abc import ABC, abstractmethod

from decimal import Decimal, ROUND_HALF_UP
from PyQt5.QtWidgets import QMainWindow, QAction, QApplication, QToolTip, QFileDialog
from PyQt5.Qt import QPushButton, QWidget, QColor, QTableWidget, QTableWidgetItem,\
    QHBoxLayout, QVBoxLayout, QGroupBox, QComboBox
from PyQt5.QtGui import QFont

__all__ = []
__version__ = 0.1
__date__ = '2018-09-27'
__updated__ = '2018-09-27'

GSI_16_LEN = 24



class GsiWord(ABC):
    def __init__(self, raw_word_str, widgetText):
        self.validate_error = str("")
        self.valid_widget_data = True
        self.raw_word_str = raw_word_str
        self.word_index = raw_word_str[0:2]
        self.sign = raw_word_str[6]
        self.value_string = widgetText
        #self.widgetItem = GsiTableWidgetItem(widgetText, raw_word_str)

    @abstractmethod
    def _createWidgetText(self):
        pass


class MeasuredData(GsiWord):
    precision_map = {'0': 3, '6': 4, '8': 5}
    unit_map = {3: '0', 4: '6', 5: '8'}
    def __init__(self, raw_word_str):
        self.input_mode = raw_word_str[4]
        self.unit = raw_word_str[5]
        self.precision = self.precision_map[self.unit]
        self.data = raw_word_str[7:23]
        super().__init__(raw_word_str, self._createWidgetText())
    
    def _createWidgetText(self):
        # Last four, three or two digits are decimals depending on precision
        formattedStr = self.data.lstrip("0")[:-self.precision] + '.' + self.data.lstrip("0")[-self.precision:]
        return formattedStr

    @classmethod
    def validate(cls, val_str, unit):
        if len(val_str) <= 1 + unit:
            validate_error = str("Value has to few numbers")
            return False
        try:
            float(val_str)
        except ValueError:
            validate_error = str("Value is not a decimal value")
            return False
        return True

    @classmethod
    def encode(cls, word_str, word_index):
        dot_index = word_str.find(".")
        precision = len(word_str) - (dot_index + 1)
        # Check if negative or positive value
        if "-" in word_str:
            sign = "-"
        else:
            sign = "+"

        data_string = word_str.replace('.', '')

        gsi_word_str = word_index + "..1" + cls.unit_map[precision] + sign + data_string.zfill(16)
        return gsi_word_str

    def set_precision(self, precision):
        if precision == "0.001":
            self.precision = 3
        elif precision == "0.0001":
            self.precision = 4
        else:
            self.precision = 5
        current_value = Decimal(float(self.widgetItem.text()))
        new_value = Decimal(current_value.quantize(Decimal(precision), rounding=ROUND_HALF_UP))
        self.widgetItem.setText(str(new_value))

class PointNumber(GsiWord):
    word_index = "11"
    def __init__(self, raw_word_str):
        self.block_no = raw_word_str[2:6]
        self.point_id = raw_word_str[7:23]
        self.value_string = self._createWidgetText()
        super().__init__(raw_word_str, self._createWidgetText())
        
    def _createWidgetText(self):
        return self.point_id.lstrip("0")
    
    def set_block_number(self, block_number):
        self.block_no = block_number.zfill(4)

    @classmethod
    def validate(cls, val_str):
        return True

    @classmethod
    def encode(cls, word_str, block_no):
        # ToDo Is it always positive?
        sign = "+"
        gsi_word_str = cls.word_index + str(block_no + 1).zfill(4) + sign + \
        word_str.zfill(16)
        return gsi_word_str
        
class Attribute(GsiWord):
    def __init__(self, raw_word_str):
        self.attribute_str = raw_word_str[7:23]
        self.value_string = self._createWidgetText()
        super().__init__(raw_word_str, self._createWidgetText())
    
    def _createWidgetText(self):
        return self.attribute_str.lstrip("0")

    @classmethod
    def validate(cls, val_str):
        return True

    @classmethod
    def encode(cls, str, word_index):
        if str.startswith("-"):
            sign = "-"
        else:
            sign = "+"
        gsi_word_str = word_index + "...." + sign + str.zfill(16)
        return gsi_word_str
        
class GsiObject():
    gsi_word_index = {'11': '0', '81': '1', '82': '2', '83': '3', '72': '4',\
                       '73': '5', '74': '6', '75': '7'}

    measured_data_wi = {1: '81', 2: '82', 3: '83', 4: '72', 5: '73', 6: '74', 7: '75'}
    
    def __init__(self, raw_string):
        self.raw_string = raw_string
        self.gsi_words = self.create_gsi_words()
        
    def create_gsi_words(self):
        if(self.raw_string[0] != "*"):
            return None
        else:
            self.raw_string = self.raw_string[1:-1] 
            
            raw_words = [self.raw_string[i:i+GSI_16_LEN] for i in range(0, len(self.raw_string), GSI_16_LEN)]
            gsi_words = [None] * 8
            for word in raw_words:
                gsi_words[int(self.gsi_word_index[word[0:2]])] = self.create_gsi_word(word)                
            return gsi_words
        
    def create_gsi_word(self, word):
        # peak at WI number
        if word[0:2] == "11":
            return PointNumber(word) 
        elif int(word[0:2]) in range(81,84):
            return MeasuredData(word)        
        elif int(word[0:2]) in range(72,79):
            return Attribute(word) 
        else:
            return None

    @classmethod
    def validate_words(cls, gsi_words, unit):
        # Validate all words in GSI Object
        validated_words = 0
        for col_number, word in enumerate(gsi_words):
            if col_number == 0:
                validated = PointNumber.validate(word)
            elif 0 < col_number <= 3:
                validated = MeasuredData.validate(word, unit)
            else:
                validated = Attribute.validate(word)
            if(validated):
               validated_words += 1

        if validated_words == len(gsi_words):
            return True
        else:
            return False

    @classmethod
    def encode_to_gsi(self, gsi_words, row):
        # Set correct block number in first GSI Word
        gsi_word_list = ["*"]
        # Then decode word for word
        for col_number, word in enumerate(gsi_words):
            word_str = str()
            if col_number == 0:
                # Set correct block number (row number) in first GSI Word
                word_str = PointNumber.encode(word, row)
            elif 0 < col_number <= 3:
                word_str = MeasuredData.encode(word, self.measured_data_wi[col_number])
            else:
                word_str = Attribute.encode(word, self.measured_data_wi[col_number])

            gsi_word_list.append( word_str  + " ")
        return ''.join(gsi_word_list)

    def set_precision(self, precision):
        for word in self.gsi_words:
            if int(word.word_index) in range(81, 84):
                word.set_precision(precision)

        

class CoEditorMainWin(QMainWindow):
    
    def __init__(self):
        super().__init__() 
        self.currentFile = None
        self.gsi_objects = list()
        self.initUI()
        self.precision = 3
       
    def closeEvent(self, event):     
        event.accept()        
    
        
    def initUI(self): 
        # File Menu 
        QToolTip.setFont(QFont('SansSerif', 10))     
        self.menubar = self.menuBar()
        self.fileMenu = self.menubar.addMenu('File')
        self.openFileAct = QAction('Open File...', self)
        self.openFileAct.setToolTip("Open GSI file")
        self.openFileAct.triggered.connect(self._choose_gsi_file)
        self.fileMenu.addAction(self.openFileAct)
               
        ## Add the central widget
        self.mainWidget = MainWidget(self)
        self.setCentralWidget(self.mainWidget)              
        
        self.setGeometry(300, 300, 1240, 600)
        self.setWindowTitle('AK GSI Editor')    
        
        self.printFileAct = QAction('Print content...', self)
        self.printFileAct.triggered.connect(self.mainWidget._print_widget_content)
        self.fileMenu.addAction(self.printFileAct)  
        
        self.printGsiObj = QAction('Print objects...', self)
        self.printGsiObj.triggered.connect(self.print_gsi_objects)
        self.fileMenu.addAction(self.printGsiObj)  
            
        
        self.show()
    
    def _choose_gsi_file(self):
        self.currentFile, _ = QFileDialog.getOpenFileName(None, "Choose GSI file file", "", "GSI files (*.gsi)")                
        if(len(self.currentFile) != 0):
            print(self.currentFile)           
        
            coordinate_list = list()
            self.gsi_objects.clear()
            with open(self.currentFile, "r") as gsiFile:
                allLines = gsiFile.readlines()
                for line in allLines:
                    coordinate_list.append(line.split())
                    self.gsi_objects.append(GsiObject(line))
            self.mainWidget.clearTable()
            self.mainWidget.fillTable(self.gsi_objects)
    
    def saveGsiFile(self):

        # Validate all GSI Objects
        if self._validate_gsi_objects():

            # Find out path to current file
            (current_dir, current_file) = os.path.split(self.currentFile)
            (shortName, extension) = os.path.splitext(current_file)

            saveDir = os.path.dirname(current_dir) +"/Justerade"
            saveFile = shortName +"_just"+ extension

            # Create Save directory (on level up)
            if not os.path.isdir(saveDir):
                os.makedirs(saveDir)

            fileName, _ = QFileDialog.getSaveFileName(None, "Choose data base file", os.path.join(saveDir, saveFile), "GSI files (*.gsi)")

            gsi_string_list = list()
            if fileName:
                with open(fileName, "w") as targetFile:
                    for row in range (0, self.mainWidget.tableWidget.rowCount()):
                        gsi_word_list = list()
                        for column in range (self.mainWidget.tableWidget.columnCount()):
                            gsi_word_list.append(self.mainWidget.tableWidget.item(row, column).text())
                        gsi_string_list.append(GsiObject.encode_to_gsi(gsi_word_list, row))

                    for line in gsi_string_list:
                        targetFile.write(line + "\n")
        else:
            print("Error in data")
            
    def print_gsi_objects(self):
        for gsiObj in self.gsi_objects:
            for word in gsiObj.gsi_words:
                if len(word.value_string) != 0:
                    print(word.value_string)
                    
    def remove_gsi_object(self, pointNoRawStr):
        for idx, gsiObj in enumerate(self.gsi_objects):
            if gsiObj.gsi_words[0].raw_word_str == pointNoRawStr:
                del self.gsi_objects[idx]
                break

    def _validate_gsi_objects(self):
        validated_objects = 0
        # Validate line for line
        for row in range(0, self.mainWidget.tableWidget.rowCount()):
            gsi_word_list = list()
            for column in range(self.mainWidget.tableWidget.columnCount()):
                gsi_word_list.append(self.mainWidget.tableWidget.item(row, column).text())
            if GsiObject.validate_words(gsi_word_list, self.precision):
                validated_objects += 1

        if validated_objects == self.mainWidget.tableWidget.rowCount():
            return True
        else:
            return False

        
    
# class GsiTableWidgetItem(QTableWidgetItem):
#     def __init__(self, valueStr, raw_word_str):
#         self.raw_word_str = raw_word_str
#         super().__init__(valueStr)


class MainWidget(QWidget):
    precision_list = ["0.001", "0.0001", "0.00001"]
    precision_strs = {3: "0.001", 4: "0.0001", 5: "0.00001"}

    def __init__(self, parent):
        super(MainWidget, self).__init__(parent)
        self.initUI() 
    
    def initUI(self):
        
        mainWidgetVboxLayout = QVBoxLayout()
        
        # Row Buttons
        commandBox  = QGroupBox()
        commandBox.setTitle("Radoperationer")
        commandLayout = QVBoxLayout()
        
        self.addNewRowBtn = QPushButton("Lägg till rad")
        self.delNewRowBtn = QPushButton("Ta bort rad")         
        self.addNewRowBtn.setToolTip("Lägg till en ny rad")
        self.delNewRowBtn.setToolTip("Radera valda rader")
        self.addNewRowBtn.clicked.connect(self.add_row)
        self.delNewRowBtn.clicked.connect(self.delete_row)

        commandLayout.addWidget(self.addNewRowBtn) 
        commandLayout.addWidget(self.delNewRowBtn)
        commandBox.setLayout(commandLayout)        
        
        # File buttons
        fileBox  = QGroupBox()
        fileBox.setTitle("Filoperationer")
        fileBoxLayout = QVBoxLayout()
        
        self.openFileBtn = QPushButton("Öppna fil")
        self.saveFileBtn = QPushButton("Spara fil")         
        self.openFileBtn.setToolTip("Öppna en ny GSI-fil")
        self.saveFileBtn.setToolTip("Spara som en ny GSI-fil")
        self.openFileBtn.clicked.connect(self.parent()._choose_gsi_file)
        self.saveFileBtn.clicked.connect(self.parent().saveGsiFile)

        fileBoxLayout.addWidget(self.openFileBtn) 
        fileBoxLayout.addWidget(self.saveFileBtn)
        fileBox.setLayout(fileBoxLayout)

        # Settings box
        precisionBox = QGroupBox()
        precisionBox.setTitle("Ändra Precision")
        precisionBoxLayout = QVBoxLayout()

        self.precisionCombo = QComboBox()
        self.precisionCombo.addItems(self.precision_list)

        precisionBoxLayout.addWidget(self.precisionCombo)
        #valueBoxLayout.addStretch(1)
        precisionBox.setLayout(precisionBoxLayout)
        self.precisionCombo.activated[str].connect(self.set_precision)


        controlBoxHboxLayout = QHBoxLayout()
        controlBoxHboxLayout.addWidget(commandBox)
        controlBoxHboxLayout.addSpacing(40)
        controlBoxHboxLayout.addWidget(fileBox)
        controlBoxHboxLayout.addSpacing(40)
        controlBoxHboxLayout.addWidget(precisionBox)
        controlBoxHboxLayout.addStretch(1)
        mainWidgetVboxLayout.addLayout(controlBoxHboxLayout)

        # Table widget        
        self.tableWidget = QTableWidget()
        self.tableWidget.setRowCount(30)
        self.tableWidget.setColumnCount(8)
        
        # Header stylesheet
        stylesheet = "QHeaderView::section{Background-color:rgb(196,214,255); gridline-color: rgb(214, 214, 214)}"
        self.tableWidget.setStyleSheet(stylesheet)
           
        
        self.tableWidget.setHorizontalHeaderLabels(["Punkt ID", "Y-koordinat", "X-koordinat", "Höjd över havet", "Kod", "Attribut 1", "Attribut 2", "Attribut 3"])
        font = QFont()
        font.setItalic(True)
        font.setPointSize(10)
        

        for idx in range(0, self.tableWidget.columnCount()):
            self.tableWidget.horizontalHeaderItem(idx).setFont(font)
            self.tableWidget.setColumnWidth(idx, 145) 
                         
        
        mainWidgetVboxLayout.addWidget(self.tableWidget)
        self.setLayout(mainWidgetVboxLayout)        
        
        
        self.setGeometry(0, 0, 1240, 600)
        pal = self.palette()
        pal.setColor(self.backgroundRole(), QColor(255, 247, 204))
        self.setPalette(pal)

        self.setAutoFillBackground(True)
        self.setWindowTitle('Buttons')     
        
    def delete_row(self):        
        rows = self.tableWidget.selectionModel().selectedRows()
        if len(rows) != 0:
            for selRow in rows:
                #pointNoRawStr = self.tableWidget.item(selRow.row(), 0).raw_word_str
                #self.parent().remove_gsi_object(pointNoRawStr)
                self.tableWidget.removeRow(selRow.row())
    
    def add_row(self):
        rows = self.tableWidget.selectionModel().selectedRows()
        if len(rows) != 0:
            self.tableWidget.insertRow(rows[0].row())
        else:
            self.tableWidget.insertRow(self.tableWidget.rowCount())

    def clearTable(self):
        for i in reversed(range(self.tableWidget.rowCount())):
            self.tableWidget.removeRow(i)


    def fillTable(self, gsi_objects):
        precision_val = 3
        self.tableWidget.setRowCount(len(gsi_objects))
        for idx, gsiObj in enumerate(gsi_objects):
            for posIdx, word in enumerate(gsiObj.gsi_words):
                # Create new Item here
                self.tableWidget.setItem(idx, posIdx, QTableWidgetItem(word.value_string))
                if idx == 0 and word.word_index == "81":
                    precision_val = word.precision
                    self.parent().precision = precision_val

        # Set precision value in combobox
        self.precisionCombo.setCurrentText(self.precision_strs[precision_val])
                
    def _print_widget_content(self):
        for idx in range(0, self.tableWidget.rowCount() -2):
            for posIdx in range(0, self.tableWidget.columnCount()-1):     
                if len(self.tableWidget.item(idx, posIdx).text()) != 0:
                    print(self.tableWidget.item(idx, posIdx).text())

    def set_precision(self, precision):
        for row in range(self.tableWidget.rowCount()):
            for column in range(1, 4):
                current_value = Decimal(float(self.tableWidget.item(row, column).text()))
                new_value = Decimal(current_value.quantize(Decimal(precision), rounding=ROUND_HALF_UP))
                self.tableWidget.item(row, column).setText(str(new_value))
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainWin = CoEditorMainWin()
    sys.exit(app.exec_())

#     sys.exit(main())