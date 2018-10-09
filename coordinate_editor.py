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

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
from PyQt5.QtWidgets import QMainWindow, QAction, QApplication, QToolTip, QFileDialog
from PyQt5.Qt import QPushButton, QWidget, QColor, QTableWidget, QTableWidgetItem,\
    QHBoxLayout, QVBoxLayout, QGroupBox
from PyQt5.QtGui import QFont

__all__ = []
__version__ = 0.1
__date__ = '2018-09-27'
__updated__ = '2018-09-27'

GSI_16_LEN = 24



class GsiWord():
    def __init__(self, raw_word_str, widgetText):
        self.raw_word_str = raw_word_str
        self.word_index = raw_word_str[0:2]
        self.sign = raw_word_str[6]
        self.widgetItem = GsiTableWidgetItem(widgetText, raw_word_str)        
            

class MeasuredData(GsiWord):
    def __init__(self, raw_word_str):
        self.input_mode = raw_word_str[4]
        self.units = raw_word_str[5]
        self.data = raw_word_str[7:23]
        super().__init__(raw_word_str, self.getWidgetText())
    
    def getWidgetText(self):
        # Last four digits are decimals        
        formattedStr = self.data.lstrip("0")[:-4] + ',' + self.data.lstrip("0")[-4:]
        return formattedStr
    
    def encode(self):
        gsi_word_str = self.word_index + "..16" + self.sign + \
        self.data.zfill(16)
        return gsi_word_str

class PointNumber(GsiWord):
    def __init__(self, raw_word_str):
        self.block_no = raw_word_str[2:6]
        self.point_id = raw_word_str[7:23]
        super().__init__(raw_word_str, self.getWidgetText())
        
    def getWidgetText(self):
        return self.point_id.lstrip("0")
    
    def set_block_number(self, block_number):
        self.block_no = block_number.zfill(4)
        
    def encode(self):
        gsi_word_str = self.word_index + self.block_no + self.sign + \
        self.point_id.zfill(16) 
        return gsi_word_str   
        
        
        
class Attribute(GsiWord):
    def __init__(self, raw_word_str):
        self.attribute_str = raw_word_str[7:23]
        super().__init__(raw_word_str, self.getWidgetText()) 
    
    def getWidgetText(self):
        return self.attribute_str.lstrip("0")         
    
    def encode(self):
        gsi_word_str = self.word_index + "...." + self.sign + self.attribute_str.zfill(16)
        return gsi_word_str
        
class GsiObject():
    gsi_word_index = {'11': '0', '81': '1', '82': '2', '83': '3', '72': '4',\
                       '73': '5', '74': '6', '75': '7'} 
    
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
    
    def encode_to_gsi(self, block_number):
                
        # Set correct block number in first GSI Word
        self.gsi_words[0].set_block_number(block_number)
        gsi_word_list = ["*"]
        # Then decode word for word
        for word in self.gsi_words:
            gsi_word_list.append(word.encode() + " ")
        return ''.join(gsi_word_list)
        

class CoEditorMainWin(QMainWindow):
    
    def __init__(self):
        super().__init__() 
        self.currentFile = None
        self.gsi_objects = list()
        self.initUI()
       
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
            
            with open(self.currentFile, "r") as gsiFile:
                allLines = gsiFile.readlines()
                for line in allLines:
                    coordinate_list.append(line.split())
                    self.gsi_objects.append(GsiObject(line))            
            self.mainWidget.fillTable(self.gsi_objects)
    
    def saveGsiFile(self):
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
                for point_num, gsiObj in enumerate(self.gsi_objects):
                    gsi_string_list.append(gsiObj.encode_to_gsi(str(point_num)))
                
                for line in gsi_string_list:
                    targetFile.write(line + "\n")
            
    def print_gsi_objects(self):
        for gsiObj in self.gsi_objects:
            for word in gsiObj.gsi_words:
                if len(word.widgetItem.text()) != 0:
                    print(word.widgetItem.text())
                    
    def remove_gsi_object(self, pointNoRawStr):
        for idx, gsiObj in enumerate(self.gsi_objects):
            if gsiObj.gsi_words[0].raw_word_str == pointNoRawStr:
                del self.gsi_objects[idx]
                break
            
        
    
class GsiTableWidgetItem(QTableWidgetItem): 
    def __init__(self, valueStr, raw_word_str): 
        self.raw_word_str = raw_word_str
        super().__init__(valueStr)


class MainWidget(QWidget):
    
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
       
       
        controlBoxHboxLayout = QHBoxLayout()        
        controlBoxHboxLayout.addWidget(commandBox)
        controlBoxHboxLayout.addSpacing(40)
        controlBoxHboxLayout.addWidget(fileBox)
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
                pointNoRawStr = self.tableWidget.item(selRow.row(), 0).raw_word_str
                self.parent().remove_gsi_object(pointNoRawStr)
                self.tableWidget.removeRow(selRow.row())
    
    def add_row(self):
        # Todo
        print("add_row")
    
    def fillTable(self, gsi_objects):
        for idx, gsiObj in enumerate(gsi_objects):
            for posIdx, word in enumerate(gsiObj.gsi_words):                
                self.tableWidget.setItem(idx, posIdx, word.widgetItem)
                
    def _print_widget_content(self):
        for idx in range(0, self.tableWidget.rowCount() -2):
            for posIdx in range(0, self.tableWidget.columnCount()-1):     
                if len(self.tableWidget.item(idx, posIdx).text()) != 0:
                    print(self.tableWidget.item(idx, posIdx).text())
        

        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainWin = CoEditorMainWin()
    sys.exit(app.exec_())

#     sys.exit(main())