import sys
import os.path
import functools
from decimal import Decimal, ROUND_HALF_UP
from PyQt5.QtWidgets import QMainWindow, QAction, QApplication, QToolTip, QFileDialog, QMessageBox, QLabel
from PyQt5.Qt import QPushButton, QWidget, QColor, QTableWidget, QTableWidgetItem, \
    QHBoxLayout, QVBoxLayout, QGroupBox, QComboBox, QGridLayout

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QKeySequence

__all__ = []
__version__ = 0.2
__date__ = '2018-09-27'
__updated__ = '2020-10-02'

GSI_16_LEN = 24


class GsiTableWidget(QTableWidget):
    def __init__(self, parent):
        QTableWidget.__init__(self, parent)

    def keyPressEvent(self, event):
        # One or more rows selected
        selected_rows = self.selectionModel().selectedRows()
        if len(selected_rows) != 0:
            if event.key() == Qt.Key_Insert and event.modifiers() != Qt.ShiftModifier:
                self.model().insertRows(selected_rows[0].row(), len(selected_rows))
                self.insert_rows(selected_rows[0].row(), len(selected_rows))
                return
            elif event.key() == Qt.Key_Insert and event.modifiers() == Qt.ShiftModifier:
                self.model().insertRows(selected_rows[0].row() + 1, len(selected_rows))
                self.insert_rows(selected_rows[0].row() + 1, len(selected_rows))
                return
            if event.key() == Qt.Key_Delete:
                for selRow in reversed(selected_rows):
                    self.model().removeRow(selRow.row())
                return
        # Insert row at the end
        else:
            if event.key() == Qt.Key_Insert:
                self.model().insertRows(self.model().rowCount(), 1)
                self.insert_rows(self.model().rowCount(), 1)
                return

        # One or more cells are selected
        if self.selectedIndexes():
            if event.key() == Qt.Key_Delete:
                for index in self.selectedIndexes():
                    self.model().setData(index, "")

            if QKeySequence(event.key() + int(event.modifiers())) == QKeySequence("Ctrl+C"):
                text = ""
                top = self.selectionModel().selection().first().top()
                bottom = self.selectionModel().selection().first().bottom()
                left = self.selectionModel().selection().first().left()
                right = self.selectionModel().selection().first().right()

                for i in range(top, bottom + 1):
                    row_contents = []
                    for j in range(left, right + 1):
                        cell_str = self.model().index(i, j).data()
                        row_contents.append(cell_str)
                    row = "\t"
                    row = row.join(row_contents)
                    text += row + "\n"
                QApplication.clipboard().setText(text)

            if QKeySequence(event.key() + int(event.modifiers())) == QKeySequence("Ctrl+V"):
                text = QApplication.clipboard().text()
                row_list = [x for x in text.split("\n") if x != '']

                selected = self.selectedIndexes()[0]
                init_row = selected.row()
                init_column = selected.column()

                for i in range(len(row_list)):
                    column_list = row_list[i].split("\t")
                    for j in range(len(column_list)):
                        self.model().setData(self.model().index(init_row + i, init_column + j), column_list[j])

    def insert_rows(self, row, count):
        for rowNr in range(count):
            for column in range(8):
                if column is 0:
                    self.setItem(row + rowNr, column, PointNumber())
                elif column in range(1, 4):
                    self.setItem(row + rowNr, column, MeasuredData())
                elif column in range(4, 8):
                    self.setItem(row + rowNr, column, Attribute())


class GsiWord(QTableWidgetItem):
    def __init__(self, raw_word_str, widget_text):
        if widget_text is not "":
            self.validate_error = str("")
            self.valid_widget_data = True
            self.raw_word_str = raw_word_str
            self.word_index = raw_word_str[0:2]
            self.sign = raw_word_str[6]
            if self.sign == "-":
                self.value_string = self.sign + widget_text
            else:
                self.value_string = widget_text
        else:
            self.value_string = widget_text
        super().__init__(self.value_string)


class MeasuredData(GsiWord):
    precision_map = {'0': 3, '6': 4, '8': 5}
    unit_map = {3: '0', 4: '6', 5: '8'}

    def __init__(self, raw_word_str=""):
        if raw_word_str is not "":
            self.input_mode = raw_word_str[4]
            self.unit = raw_word_str[5]
            self.precision = self.precision_map[self.unit]
            self.data = raw_word_str[7:23]
            super().__init__(raw_word_str, self._create_widget_text())
        else:
            super().__init__(raw_word_str, raw_word_str)

    def _create_widget_text(self):
        # Last four, three or two digits are decimals depending on precision
        formatted_str = self.data.lstrip("0")[:-self.precision] + '.' + self.data.lstrip("0")[-self.precision:]
        if len(self.data.lstrip("0")[:-self.precision]) == 0:
            formatted_str = "0" + formatted_str
        return formatted_str

    def validate(self):
        if len(self.text()) <= 1 + self.precision:
            # ToDo validate_error = value_str("Value has to few numbers")
            return False
        try:
            float(super().text())
        except ValueError:
            # ToDo validate_error = value_str("Value is not a decimal value")
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

        data_string = word_str.replace('.', '').replace('-', '')

        gsi_word_str = word_index + "..1" + cls.unit_map[precision] + sign + data_string.zfill(16)
        return gsi_word_str

    def set_precision(self, precision):
        if precision == "0.001":
            self.precision = 3
        elif precision == "0.0001":
            self.precision = 4
        else:
            self.precision = 5

        if self.text() != "":

            try:
                float(super().text())
            except ValueError:
                return

            current_value = Decimal(float(self.text()))
            new_value = Decimal(current_value.quantize(Decimal(precision), rounding=ROUND_HALF_UP))
            self.setText(str(new_value))


class PointNumber(GsiWord):
    word_index = "11"

    def __init__(self, raw_word_str=""):
        if raw_word_str is not "":
            self.block_no = raw_word_str[2:6]
            self.point_id = raw_word_str[7:23]
            self.value_string = self._create_widgettext()
            super().__init__(raw_word_str, self._create_widgettext())
        else:
            super().__init__(raw_word_str, raw_word_str)

    def _create_widgettext(self):
        return self.point_id.lstrip("0")

    def set_block_number(self, block_number):
        self.block_no = block_number.zfill(4)

    def validate(self):
        return len(self.text()) != 0

    @classmethod
    def encode(cls, word_str, block_no):
        # ToDo Is it always positive?
        sign = "+"
        gsi_word_str = cls.word_index + str(block_no + 1).zfill(4) + sign + word_str.zfill(16)
        return gsi_word_str


class Attribute(GsiWord):
    def __init__(self, raw_word_str=""):
        if raw_word_str is not "":
            self.attribute_str = raw_word_str[7:23]
            self.value_string = self._create_widgettext()
            super().__init__(raw_word_str, self._create_widgettext())
        else:
            super().__init__(raw_word_str, raw_word_str)

    def _create_widgettext(self):
        return self.attribute_str.lstrip("0")

    def validate(self):
        return True

    @classmethod
    def encode(cls, value_str, word_index):
        if value_str.startswith("-"):
            sign = "-"
        else:
            sign = "+"
        gsi_word_str = word_index + "...." + sign + value_str.zfill(16)
        return gsi_word_str


class GsiObject():
    gsi_word_index = {'11': '0', '81': '1', '82': '2', '83': '3', '72': '4',
                      '73': '5', '74': '6', '75': '7'}

    measured_data_wi = {1: '81', 2: '82', 3: '83', 4: '72', 5: '73', 6: '74', 7: '75'}

    def __init__(self, raw_string):
        self.raw_string = raw_string
        self.gsi_words = self.create_gsi_words()

    def create_gsi_words(self):
        if self.raw_string[0] != "*":
            return None
        else:
            self.raw_string = self.raw_string[1:-1]

            raw_words = [self.raw_string[i:i + GSI_16_LEN] for i in range(0, len(self.raw_string), GSI_16_LEN)]
            gsi_words = [None] * 8
            for word in raw_words:
                gsi_words[int(self.gsi_word_index[word[0:2]])] = self.create_gsi_word(word)
            return gsi_words

    def create_gsi_word(self, word):
        # peak at WI number
        if word[0:2] == "11":
            return PointNumber(word)
        elif int(word[0:2]) in range(81, 84):
            return MeasuredData(word)
        elif int(word[0:2]) in range(72, 79):
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
                validated = MeasuredData.validate(word)
            else:
                validated = Attribute.validate(word)
            if (validated):
                validated_words += 1

        if validated_words == len(gsi_words):
            return True
        else:
            return False

    @classmethod
    def encode_to_gsi(cls, gsi_words, row):
        # Set correct block number in first GSI Word
        gsi_word_list = ["*"]
        # Then decode word for word
        for col_number, word in enumerate(gsi_words):
            word_str = str()
            if col_number == 0:
                # Set correct block number (row number) in first GSI Word
                word_str = PointNumber.encode(word, row)
            elif 0 < col_number <= 3:
                word_str = MeasuredData.encode(word, cls.measured_data_wi[col_number])
            else:
                word_str = Attribute.encode(word, cls.measured_data_wi[col_number])

            gsi_word_list.append(word_str + " ")
        return ''.join(gsi_word_list)

    def set_precision(self, precision):
        for word in self.gsi_words:
            if int(word.word_index) in range(81, 84):
                word.set_precision(precision)


class CoEditorMainWin(QMainWindow):
    precision_strs = {3: "0.001", 4: "0.0001", 5: "0.00001"}

    def __init__(self):
        super().__init__()
        self.currentFile = None
        self.gsi_objects = list()
        self.init_ui()
        self.precision = 3

    def closeEvent(self, event):
        event.accept()

    def init_ui(self):
        # File Menu 
        QToolTip.setFont(QFont('SansSerif', 10))
        self.menubar = self.menuBar()
        self.fileMenu = self.menubar.addMenu('File')
        self.openFileAct = QAction('Open File...', self)
        self.openFileAct.setToolTip("Open GSI file")
        self.openFileAct.triggered.connect(self._choose_gsi_file)
        self.fileMenu.addAction(self.openFileAct)

        self.saveFileAct = QAction('Save File...', self)
        self.saveFileAct.setToolTip("Save File in GSI 16 format")
        self.saveFileAct.triggered.connect(self.save_gsi_file)
        self.fileMenu.addAction(self.saveFileAct)

        # Add the central widget
        self.mainWidget = MainWidget(self)
        self.setCentralWidget(self.mainWidget)

        self.setGeometry(300, 300, 1220, 600)
        self.setWindowTitle('AK GSI-16 Editor - ' + str(__version__))

        self.show()

    def _choose_gsi_file(self):
        self.currentFile, _ = QFileDialog.getOpenFileName(None, "Choose GSI file file", "", "GSI files (*.gsi)")
        if (len(self.currentFile) != 0):
            print(self.currentFile)

            coordinate_list = list()
            self.gsi_objects.clear()
            with open(self.currentFile, "r") as gsiFile:
                all_lines = gsiFile.readlines()
                for line in all_lines:
                    coordinate_list.append(line.split())
                    self.gsi_objects.append(GsiObject(line))

            # Get current precision from first GSI object first Measured Data word
            self.precision = self.gsi_objects[0].gsi_words[1].precision

            # Update GUI
            self.mainWidget.clear_table()
            self.mainWidget.fill_table(self.gsi_objects)
            # Set precision value in combobox in MainWindow
            self.mainWidget.precisionCombo.setCurrentText(self.precision_strs[self.precision])
            self.mainWidget.precisionCombo.setEnabled(True)
            self.mainWidget.validate_values_btn.setEnabled(True)

    def save_gsi_file(self):

        # Validate all GSI Objects
        if self._validate_gsi_objects():

            # Find out path to current file
            (current_dir, current_file) = os.path.split(self.currentFile)
            (shortName, extension) = os.path.splitext(current_file)

            save_dir = current_dir
            save_file = shortName + extension

            # Create Save directory
            if not os.path.isdir(save_dir):
                os.makedirs(save_dir)

            file_name, _ = QFileDialog.getSaveFileName(None, "Choose data base file", os.path.join(save_dir, save_file),
                                                      "GSI files (*.gsi)")

            gsi_string_list = list()
            if file_name:
                with open(file_name, "w") as targetFile:
                    for row in range(0, self.mainWidget.tableWidget.rowCount()):
                        gsi_word_list = list()
                        for column in range(self.mainWidget.tableWidget.columnCount()):
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

    def remove_gsi_object(self, point_no_raw_str):
        for idx, gsiObj in enumerate(self.gsi_objects):
            if gsiObj.gsi_words[0].raw_word_str == point_no_raw_str:
                del self.gsi_objects[idx]
                break

    def _validate_gsi_objects(self, create_ok_box=False):
        validated_objects = 0
        invalid_objects = []
        # Make sure user added values have precision set
        self.mainWidget.set_precision(self.mainWidget.precisionCombo.currentText())
        # Validate line for line
        for row in range(0, self.mainWidget.tableWidget.rowCount()):
            for column in range(0, 4):  # Don't validate the Attributes or code
                if self.mainWidget.tableWidget.item(row, column) and self.mainWidget.tableWidget.item(row,
                                                                                                      column).text():
                    if self.mainWidget.tableWidget.item(row, column).validate():
                        validated_objects += 1
                    else:
                        invalid_objects.append("row: " + str(row) + " column: " + str(column))
                else:
                    invalid_objects.append("row: " + str(row) + " column: " + str(column))
            # Attributes are always valid
            for column in range(5, 9):
                validated_objects += 1

        if validated_objects == self.mainWidget.tableWidget.rowCount() * self.mainWidget.tableWidget.columnCount():
            if create_ok_box:
                msg = QMessageBox()
                msg.setWindowTitle("Validation Result")
                msg.setText("All Cells are valid")
                msg.exec_()
            else:
                return True
        else:
            # Create Messagebox
            msg = QMessageBox()
            msg.setWindowTitle("Invalid entries found")
            text_message = "Following cells have incorrect values:\n"
            for cell in invalid_objects:
                text_message = text_message + cell + "\n"
            msg.setText(text_message)
            msg.setIcon(QMessageBox.Critical)
            msg.exec_()
            return False


class MainWidget(QWidget):
    precision_list = ["0.001", "0.0001", "0.00001"]

    def __init__(self, parent):
        super(MainWidget, self).__init__(parent)
        self.init_ui()

    def init_ui(self):

        main_widget_vbox_layout = QVBoxLayout()

        # File buttons
        file_box = QGroupBox()
        file_box.setTitle("File...")
        file_box_layout = QVBoxLayout()

        self.openFileBtn = QPushButton("Open file")
        self.saveFileBtn = QPushButton("Save file")
        self.openFileBtn.setToolTip("Open a GSI-16 file")
        self.saveFileBtn.setToolTip("Save as new GSI-16 file")
        self.openFileBtn.clicked.connect(self.parent()._choose_gsi_file)
        self.saveFileBtn.clicked.connect(self.parent().save_gsi_file)

        file_box_layout.addWidget(self.openFileBtn)
        file_box_layout.addWidget(self.saveFileBtn)
        file_box.setLayout(file_box_layout)

        # Tools box
        tools_box = QGroupBox()
        tools_box.setTitle("Tools")
        tools_box_layout = QGridLayout()

        label_validate = QLabel("Validate values")
        tools_box_layout.addWidget(label_validate, 0, 0)

        self.precisionCombo = QComboBox()
        self.precisionCombo.addItems(self.precision_list)
        self.precisionCombo.setEnabled(False)
        self.precisionCombo.activated[str].connect(self.set_precision)

        self.validate_values_btn = QPushButton("Validate")
        self.validate_values_btn.setToolTip("Validate format of Measured data GSI words")
        self.validate_values_btn.clicked.connect(functools.partial(self.parent()._validate_gsi_objects, True))
        self.validate_values_btn.setEnabled(False)
        tools_box_layout.addWidget(self.validate_values_btn, 0, 1)

        label = QLabel("Change Precision")
        tools_box_layout.addWidget(label, 1, 0)
        tools_box_layout.addWidget(self.precisionCombo, 1, 1)
        tools_box.setLayout(tools_box_layout)

        control_box_hbox_layout = QHBoxLayout()
        control_box_hbox_layout.addWidget(file_box)
        control_box_hbox_layout.addSpacing(40)
        control_box_hbox_layout.addWidget(tools_box)
        control_box_hbox_layout.addStretch(1)
        main_widget_vbox_layout.addLayout(control_box_hbox_layout)

        # Table widget
        self.tableWidget = GsiTableWidget(self)
        # self.tableWidget.setRowCount(30)
        self.tableWidget.setColumnCount(8)

        # Header stylesheet
        stylesheet = "QHeaderView::section{Background-color:rgb(196,214,255); gridline-color: rgb(214, 214, 214)}"
        self.tableWidget.setStyleSheet(stylesheet)

        self.tableWidget.setHorizontalHeaderLabels(
            ["Pointnumber", "Y-coordinate", "X-coordinate", "Elevation", "Code", "Attribute 1", "Attribute 2",
             "Attribute 3"])
        font = QFont()
        font.setItalic(True)
        font.setPointSize(10)

        for idx in range(0, self.tableWidget.columnCount()):
            self.tableWidget.horizontalHeaderItem(idx).setFont(font)
            self.tableWidget.setColumnWidth(idx, 145)

        main_widget_vbox_layout.addWidget(self.tableWidget)
        self.setLayout(main_widget_vbox_layout)

        self.setGeometry(0, 0, 1240, 600)
        pal = self.palette()
        pal.setColor(self.backgroundRole(), QColor(255, 247, 204))
        self.setPalette(pal)

        self.setAutoFillBackground(True)
        self.setWindowTitle('Buttons')

    def clear_table(self):
        for i in reversed(range(self.tableWidget.rowCount())):
            self.tableWidget.removeRow(i)

    def fill_table(self, gsi_objects):
        self.tableWidget.setRowCount(len(gsi_objects))
        for idx, gsiObj in enumerate(gsi_objects):
            for posIdx, word in enumerate(gsiObj.gsi_words):
                # Add new Item (GSI Word) here
                self.tableWidget.setItem(idx, posIdx, word)

    def set_precision(self, precision):
        for row in range(self.tableWidget.rowCount()):
            for column in range(1, 4):
                self.tableWidget.item(row, column).set_precision(precision)
                self.parent().precision = len(precision.split(".")[1])


if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainWin = CoEditorMainWin()
    sys.exit(app.exec_())
