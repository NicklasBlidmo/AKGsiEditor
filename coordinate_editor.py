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

import sys

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

#*110001+000RTCM-Ref 0454 81...6+0000006742974308 82...6+0000065558922759 83...6+0000000000436354 72....+0000000000000000 73....+0000000000000000 74....+0000000000000000 75....+0000000000000000 
#*110002+0000000000020363 81...6+0000006774180503 82...6+0000065560868658 83...6+0000000000256145 72....+0000000000002022 73....+00000000000000KN 74....+0000000000000001 75....+0000000000000000 

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
        super().__init__(raw_word_str, self.getText())
    
    def getText(self):
        # Last four digits are decimals        
        formattedStr = self.data.lstrip("0")[:-4] + ',' + self.data.lstrip("0")[-4:]
        return formattedStr
                                      

class PointNumber(GsiWord):
    def __init__(self, raw_word_str):
        self.block_no = raw_word_str[2:6]
        self.point_id = raw_word_str[7:23]
        super().__init__(raw_word_str, self.point_id.lstrip("0"))
        
    def getText(self):
        return self.point_id
        
class Attribute(GsiWord):
    def __init__(self, raw_word_str):
        self.attribute_str = raw_word_str[7:23]
        super().__init__(raw_word_str, self.attribute_str.lstrip("0")) 
    
    def getText(self):
        return self.attribute_str               
        
class GsiObject():
    gsi_word_index = {'11': '0', '81': '1', '82': '2', '83': '3', '72': '4', '73': '5', '74': '6', '75': '7'} 
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
            

def main(argv=None): # IGNORE:C0111
    '''Command line options.'''

    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)
    try:
        # Setup argument parser
        parser = ArgumentParser("AK Coordinate parser", formatter_class=RawDescriptionHelpFormatter)       
        parser.add_argument("-v", "--verbose", action="count", default= 0, help="set verbosity level [default: %(default)s]")
        parser.add_argument("source_file", help="source GSI file to parse")

        # Process arguments
        args = parser.parse_args()

        verbose = args.verbose
 
        if verbose > 0:
            print("Verbose mode on")
        
        coordinate_list = list()  
        gsi_objects = list()
        with open(args.source_file, "r") as gsiFile:
            allLines = gsiFile.readlines()
            for line in allLines:
                coordinate_list.append(line.split())
                gsi_objects.append(GsiObject(line))
        
        for cord in coordinate_list:
            print(cord)
              

    except Exception as e:
        sys.stderr.write("for help use --help  Exception: " + e )
        return 2

class CoEditorMainWin(QMainWindow):
    
    def __init__(self):
        super().__init__() 
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
        self.setWindowTitle('AK Coordinate editor')    
        
        self.printFileAct = QAction('Print content...', self)
        self.printFileAct.triggered.connect(self.mainWidget._print_widget_content)
        self.fileMenu.addAction(self.printFileAct)  
        
        self.printGsiObj = QAction('Print objects...', self)
        self.printGsiObj.triggered.connect(self.print_gsi_objects)
        self.fileMenu.addAction(self.printGsiObj)  
            
        
        self.show()
    
    def _choose_gsi_file(self):
        fileName, _ = QFileDialog.getOpenFileName(None, "Choose GSI file file", "", "GSI files (*.gsi)")                
        if(len(fileName) != 0):
            print(fileName)           
        
            coordinate_list = list()  
            self.gsi_objects = list()
            
            with open(fileName, "r") as gsiFile:
                allLines = gsiFile.readlines()
                for line in allLines:
                    coordinate_list.append(line.split())
                    self.gsi_objects.append(GsiObject(line))            
            self.mainWidget.fillTable(self.gsi_objects)
            
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
        
        # Buttons
        commandBox  = QGroupBox()
        commandBox.setTitle("Commands")
        commandLayout = QVBoxLayout()
        
        self.addNewRowBtn = QPushButton("Add New Row")
        self.delNewRowBtn = QPushButton("Delete Row")         
        self.addNewRowBtn.setToolTip("Add new row above selected row")
        self.delNewRowBtn.setToolTip("Add new row above selected row")
        self.addNewRowBtn.clicked.connect(self.add_row)
        self.delNewRowBtn.clicked.connect(self.delete_row)

        commandLayout.addWidget(self.addNewRowBtn) 
        commandLayout.addWidget(self.delNewRowBtn)
        commandBox.setLayout(commandLayout)        
        commandHboxLayout = QHBoxLayout()        
        commandHboxLayout.addWidget(commandBox)
        commandHboxLayout.addStretch(1)
        mainWidgetVboxLayout.addLayout(commandHboxLayout)  
        
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
#         pal = self.palette()
#         pal.setColor(self.backgroundRole(), QColor(232, 252, 210))
#         self.setPalette(pal)

        self.setAutoFillBackground(True)
        self.setWindowTitle('Buttons')     
        
    def delete_row(self):        
        rows = self.tableWidget.selectionModel().selectedRows()
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