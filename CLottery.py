import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, QMessageBox, QDialog, QFormLayout, QDoubleSpinBox, QListWidget, QScrollArea, QGridLayout
from PyQt6.QtGui import QIcon, QFont, QPixmap, QKeySequence, QShortcut, QDesktopServices
from PyQt6.QtCore import Qt, QSettings, QTimer, QRectF, pyqtSlot, QUrl, QSize
import random
import os
import json

# 定义隐藏设置对话框类
class HiddenSettingsDialog(QDialog):
    def __init__(self, names, probabilities, parent=None):
        super().__init__(parent)
        self.names = names  
        self.probabilities = probabilities  
        self.probabilitySpinBoxes = {}  
        self.initUI() 

    def initUI(self):
        self.setWindowTitle('概率设置')
        self.setGeometry(300, 300, 400, 300)
        self.setStyleSheet("""
            QDialog { border-radius: 10px; background-color: #f0f0f0; }
            QDoubleSpinBox { border: 1px solid #ccc; border-radius: 5px; padding: 5px; width: 100px; height: 30px; }
        """)

        # 创建一个垂直布局管理器
        main_layout = QVBoxLayout(self)

        # 创建滚动区域，用于容纳可能超出窗口大小的内容
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)  # 允许滚动区域内的控件调整大小
        main_layout.addWidget(scroll_area)

        # 创建一个容器小部件，并设置表单布局
        container_widget = QWidget()
        layout = QFormLayout(container_widget)
        scroll_area.setWidget(container_widget)

        # 归一化概率值，确保总和为100%
        total_probability = sum(self.probabilities.values())
        if total_probability > 0:
            for name in self.names:
                self.probabilities[name] = (self.probabilities[name] / total_probability) * 100

        # 为每个名字创建一个概率输入框
        for name in self.names:
            probabilitySpinBox = QDoubleSpinBox()
            probabilitySpinBox.setRange(0, 100)  # 设置概率值的范围
            probabilitySpinBox.setDecimals(2)  # 设置小数点后的位数
            probabilitySpinBox.setValue(self.probabilities.get(name, 0))  # 设置初始值
            probabilitySpinBox.valueChanged.connect(lambda value, n=name: self.updateDynamicProbabilities(n, value))  # 连接信号到槽函数
            layout.addRow(name, probabilitySpinBox)  # 将名字和对应的输入框添加到表单布局中
            self.probabilitySpinBoxes[name] = probabilitySpinBox  # 存储输入框控件

        # 添加平均分配概率按钮
        equalizeButton = QPushButton('重置')
        equalizeButton.clicked.connect(self.equalizeProbabilities)  # 连接按钮点击信号到槽函数
        main_layout.addWidget(equalizeButton)  # 将按钮添加到布局中

        # 添加保存按钮
        saveButton = QPushButton('保存')
        saveButton.clicked.connect(self.saveProbabilities)  # 连接按钮点击信号到槽函数
        main_layout.addWidget(saveButton)  # 将按钮添加到布局中

        self.setLayout(main_layout)  # 设置对话框的主布局

    def updateDynamicProbabilities(self, name, value):
        # 更新指定名字的概率值
        self.probabilities[name] = value
        total_probability = sum(self.probabilities.values())
        
        # 重新分配剩余概率值
        if total_probability != 100:
            remaining_prob = 100 - total_probability
            remaining_names = [n for n in self.names if n != name]
            if remaining_names:
                num_remaining = len(remaining_names)
                equal_prob = remaining_prob / num_remaining
                for n in remaining_names:
                    # 断开信号以避免递归调用
                    self.probabilitySpinBoxes[n].valueChanged.disconnect()
                    self.probabilities[n] += equal_prob
                    self.probabilitySpinBoxes[n].setValue(self.probabilities[n])
                    # 重新连接信号
                    self.probabilitySpinBoxes[n].valueChanged.connect(lambda value, n=n: self.updateDynamicProbabilities(n, value))

    def equalizeProbabilities(self):
        # 平均分配概率值，确保总和为100%
        num_names = len(self.names)
        if num_names > 0:
            equal_prob = 100 / num_names
            for name in self.names:
                self.probabilities[name] = equal_prob
                self.probabilitySpinBoxes[name].setValue(equal_prob)

    def saveProbabilities(self):
        # 保存当前的概率值
        for name, spinBox in self.probabilitySpinBoxes.items():
            self.probabilities[name] = spinBox.value()
        self.accept()

# 定义抽号对话框类
class LotteryResultDialog(QDialog):
    def __init__(self, names, probabilities, parent=None):
        super().__init__(parent)
        self.names = names
        self.probabilities = probabilities
        self.startButton = None  
        self.winner = None 
        self.initUI()

    def initUI(self):
        self.setWindowTitle('抽号')
        self.setGeometry(300, 300, 400, 200)
        self.setStyleSheet("""
            QDialog { border-radius: 10px; background-color: #f0f0f0; }
            QLabel { font-size: 24px; color: #333; }
        """)

        layout = QVBoxLayout()

        self.resultLabel = QLabel('点击“开始”按钮开始抽号...')
        self.resultLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.resultLabel)

        self.startButton = QPushButton('开始')
        self.startButton.clicked.connect(self.startLottery)
        layout.addWidget(self.startButton)

        self.setLayout(layout)

    def startLottery(self):
        if self.startButton is not None:  # 检查 startButton 是否已初始化
            self.startButton.setEnabled(False)  

        if self.names:
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.flashNames)
            self.timer.start(100) 

            randomValue = random.uniform(0, 100)
            cumulativeProbability = 0
            for name in self.names:
                cumulativeProbability += self.probabilities[name]
                if randomValue <= cumulativeProbability:
                    self.winner = name 
                    break

            # 延迟显示最终结果，并解锁“开始”按钮
            QTimer.singleShot(3000, self.showResultAndEnableButton)  
        else:
            QMessageBox.warning(self, '警告', '没有名字可供抽取，请先添加名字！')
            if self.startButton is not None:  # 检查 startButton 是否已初始化
                self.startButton.setEnabled(True) 

    def showResultAndEnableButton(self):
        self.showResult()
        if self.startButton is not None:  # 检查 startButton 是否已初始化
            self.startButton.setEnabled(True)  

    def showResult(self):
        if self.winner is not None:  
            self.timer.stop()
            self.resultLabel.setText(f'幸运儿是：{self.winner}')
        else:
            self.resultLabel.setText('没有抽到任何名字！')

    def flashNames(self):
        name = random.choice(self.names)
        self.resultLabel.setText(name)

# 定义关于对话框类
class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        self.setWindowTitle('关于')
        self.setGeometry(300, 300, 400, 200)
        self.setStyleSheet("""
            QDialog { border-radius: 10px; background-color: #f0f0f0; }
            QLabel { font-size: 14px; color: #333; }
            QPushButton { border: none; text-align: center; vertical-align: middle; }
        """)

        layout = QVBoxLayout()

        aboutText = QLabel("CLottery 是一款简单的能够随机抽号的app。其提供了直观的图形化编辑窗口。\n此软件基于 PyQt6 开发，完全免费且开源。\n由 Phantom core开发")
        aboutText.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(aboutText)

        # 创建一个水平布局管理器
        buttonLayout = QHBoxLayout()

        githubButton = QPushButton()
        githubButton.setText("此项目的 GitHub")
        pixmap = QPixmap("Octicons-mark-github.svg") 
        githubButton.setIcon(QIcon(pixmap))
        githubButton.setIconSize(QSize(24, 24))  
        githubButton.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com")))  
        buttonLayout.addWidget(githubButton)

        bilibiliButton = QPushButton()
        bilibiliButton.setText("我的 哔哩哔哩 主页")
        pixmap = QPixmap("bilibili-website.favicon.svg") 
        bilibiliButton.setIcon(QIcon(pixmap))
        bilibiliButton.setIconSize(QSize(24, 24))  
        bilibiliButton.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://space.bilibili.com/3546560566659226")))  
        buttonLayout.addWidget(bilibiliButton)

        layout.addLayout(buttonLayout)
        self.setLayout(layout)

# 定义课堂抽号机类
class ClassroomLottery(QWidget):
    def __init__(self):
        super().__init__()  
        self.initUI()  
        self.names = []  
        self.probabilities = {} 
        self.loadSettings()  
        self.loadProgramState() 

    def initUI(self):
        self.setWindowTitle('课堂抽号机')
        self.setGeometry(300, 300, 400, 350)
        self.setStyleSheet("""
            QWidget {
                background-color: #f0f0f0;
                border-radius: 10px;
            }
            QPushButton {
                background-color: #007bff;
                color: white;
                border-radius: 5px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QLineEdit, QListWidget {
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 5px;
            }
            QLabel {
                font-size: 16px;
            }
        """)

        layout = QGridLayout()

        self.nameInput = QLineEdit(self)
        self.nameInput.setPlaceholderText('请输入名字')
        layout.addWidget(self.nameInput, 0, 0, 1, 2)

        addButton = QPushButton('添加名字')
        addButton.clicked.connect(self.addName)  # 连接点击信号到addName槽函数
        layout.addWidget(addButton, 0, 2)

        self.nameListWidget = QListWidget(self)
        self.nameListWidget.setAlternatingRowColors(True)
        layout.addWidget(self.nameListWidget, 1, 0, 1, 3)

        deleteButton = QPushButton('删除名字')
        deleteButton.clicked.connect(self.deleteName)  # 连接点击信号到deleteName槽函数
        layout.addWidget(deleteButton, 2, 0)

        drawButton = QPushButton('抽号')
        drawButton.clicked.connect(self.openLotteryResultDialog)  # 连接点击信号到openLotteryResultDialog槽函数
        layout.addWidget(drawButton, 2, 1)

        aboutButton = QPushButton('关于')
        aboutButton.clicked.connect(self.openAboutDialog)  # 连接点击信号到openAboutDialog槽函数
        layout.addWidget(aboutButton, 2, 2)

        self.setLayout(layout)

        # 连接输入框的回车信号到addName槽函数
        self.nameInput.returnPressed.connect(self.addName)

        # 创建快捷键，用于快速打开隐藏设置对话框
        self.hiddenShortcut = QShortcut(QKeySequence('Ctrl+Shift+H'), self)
        self.hiddenShortcut.activated.connect(self.openHiddenSettings)

    def openLotteryResultDialog(self):
        # 打开抽号结果对话框
        dialog = LotteryResultDialog(self.names, self.probabilities, self)
        # 设置新窗口的位置在原窗口的右侧
        dialog.setGeometry(self.geometry().right(), self.geometry().top(), 400, 200)
        dialog.exec()

    def openAboutDialog(self):
        # 打开关于对话框
        dialog = AboutDialog(self)
        # 设置新窗口的位置在原窗口的下方
        dialog.setGeometry(self.geometry().left(), self.geometry().bottom(), 400, 200)
        dialog.exec()

    def openHiddenSettings(self):
        # 打开隐藏设置对话框
        dialog = HiddenSettingsDialog(self.names, self.probabilities, self)
        # 设置新窗口的位置在原窗口的右侧下方
        dialog.setGeometry(self.geometry().right(), self.geometry().bottom(), 400, 300)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.saveProgramState()

    def addName(self):
        # 从输入框获取名字，并去除两端的空白字符
        name = self.nameInput.text().strip()
        
        if name and name not in self.names:
            self.names.append(name)  
            self.probabilities[name] = 100 
            # 重新计算所有概率值，确保总和为100%
            new_prob = 100 / len(self.names)
            for n in self.names:
                self.probabilities[n] = new_prob 
            self.nameInput.clear()  
            self.nameListWidget.addItem(name)  # 将名字添加到列表控件
            QMessageBox.information(self, '提示', f'已添加名字：{name}')  
            self.saveProgramState()  # 保存程序状态
            # 如果隐藏设置对话框已打开，更新它的概率值
            if hasattr(self, 'hiddenSettingsDialog') and self.hiddenSettingsDialog:
                self.hiddenSettingsDialog.updateProbabilities(self.names, self.probabilities)
        elif name in self.names:
            QMessageBox.warning(self, '警告', '名字已存在！')  
        else:
            QMessageBox.warning(self, '警告', '请输入名字！')

    def deleteName(self):
        # 获取列表控件中选中的项
        selectedItems = self.nameListWidget.selectedItems()
        if selectedItems:
            name = selectedItems[0].text()  # 获取选中项的名字
            self.names.remove(name)  # 从名字列表中移除
            del self.probabilities[name]  # 从概率字典中移除
            self.nameListWidget.takeItem(self.nameListWidget.row(selectedItems[0]))  # 从列表控件中移除
            QMessageBox.information(self, '提示', f'已删除名字：{name}') 
            self.saveProgramState()  # 保存程序状态
        else:
            QMessageBox.warning(self, '警告', '请选择要删除的名字！')

    def saveProgramState(self):
        # 将程序状态保存到JSON文件
        programState = {
            'names': self.names,
            'probabilities': self.probabilities
        }
        with open('program_state.json', 'w', encoding='utf-8') as file:
            json.dump(programState, file, ensure_ascii=False, indent=4)

    def loadProgramState(self):
        # 从JSON文件加载程序状态
        if os.path.exists('program_state.json'):
            with open('program_state.json', 'r', encoding='utf-8') as file:
                programState = json.load(file)
                self.names = programState['names']
                self.probabilities = programState['probabilities']
                self.nameListWidget.clear()
                self.nameListWidget.addItems(self.names)
            QMessageBox.information(self, '提示', '已从文件中加载程序状态。')

    def loadSettings(self):
        # 从QSettings加载设置
        settings = QSettings('ClassroomLottery', 'Settings')
        self.settingsShortcut = settings.value('shortcut', 'Ctrl+D')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ClassroomLottery()
    ex.show()
    sys.exit(app.exec())
