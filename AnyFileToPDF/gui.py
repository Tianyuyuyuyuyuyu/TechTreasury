import sys
import os
import logging
import traceback
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QPushButton, QLineEdit, QProgressBar, QTextEdit,
                            QFileDialog, QMessageBox, QLabel)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from converter import PDFConverter

class ConversionThread(QThread):
    """转换线程"""
    progress_signal = pyqtSignal(float)
    log_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    
    def __init__(self, folder_path, converter):
        super().__init__()
        self.folder_path = folder_path
        self.converter = converter
        
    def run(self):
        try:
            self.converter.convert_folder(
                self.folder_path,
                self.log_signal.emit,
                self.progress_signal.emit
            )
            self.finished_signal.emit()
        except Exception as e:
            self.error_signal.emit(str(e))

class PDFConverterGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.converter = PDFConverter()
        self.setup_ui()
        self.setup_logging()
        
    def setup_logging(self):
        """设置日志系统"""
        try:
            logging.basicConfig(level=logging.INFO)
            self.logger = logging.getLogger(__name__)
        except Exception as e:
            self.show_error("日志系统初始化失败", str(e))
            
    def setup_ui(self):
        """设置用户界面"""
        try:
            # 设置窗口属性
            self.setWindowTitle("AnyFileToPDF转换器")
            self.setMinimumSize(800, 600)
            
            # 创建中央部件
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            
            # 创建主布局
            layout = QVBoxLayout(central_widget)
            
            # 文件夹选择区域
            folder_layout = QHBoxLayout()
            self.folder_edit = QLineEdit()
            self.folder_edit.setPlaceholderText("选择要转换的文件夹...")
            browse_button = QPushButton("选择文件夹")
            browse_button.clicked.connect(self.browse_folder)
            folder_layout.addWidget(self.folder_edit)
            folder_layout.addWidget(browse_button)
            layout.addLayout(folder_layout)
            
            # 进度条
            self.progress_bar = QProgressBar()
            self.progress_bar.setRange(0, 100)
            layout.addWidget(self.progress_bar)
            
            # 日志区域
            log_label = QLabel("转换日志")
            layout.addWidget(log_label)
            self.log_text = QTextEdit()
            self.log_text.setReadOnly(True)
            layout.addWidget(self.log_text)
            
            # 按钮区域
            button_layout = QHBoxLayout()
            self.start_button = QPushButton("开始转换")
            self.start_button.clicked.connect(self.start_conversion)
            self.cancel_button = QPushButton("取消")
            self.cancel_button.clicked.connect(self.cancel_conversion)
            self.cancel_button.setEnabled(False)
            button_layout.addWidget(self.start_button)
            button_layout.addWidget(self.cancel_button)
            layout.addLayout(button_layout)
            
        except Exception as e:
            self.show_error("界面初始化失败", str(e))
            raise
            
    def show_error(self, title, message):
        """显示错误对话框"""
        QMessageBox.critical(self, title, message)
        
    def browse_folder(self):
        """选择文件夹"""
        try:
            folder_path = QFileDialog.getExistingDirectory(self, "选择文件夹")
            if folder_path:
                self.folder_edit.setText(folder_path)
        except Exception as e:
            self.show_error("选择文件夹失败", str(e))
            
    def log_message(self, message):
        """记录日志消息"""
        try:
            self.log_text.append(message)
        except Exception as e:
            self.show_error("日志记录失败", str(e))
            
    def update_progress(self, value):
        """更新进度条"""
        try:
            self.progress_bar.setValue(int(value))
        except Exception as e:
            self.show_error("更新进度失败", str(e))
            
    def start_conversion(self):
        """开始转换"""
        try:
            folder_path = self.folder_edit.text()
            if not folder_path:
                self.show_error("错误", "请选择要转换的文件夹！")
                return
                
            if not os.path.exists(folder_path):
                self.show_error("错误", "所选文件夹不存在！")
                return
                
            self.start_button.setEnabled(False)
            self.cancel_button.setEnabled(True)
            
            # 创建并启动转换线程
            self.conversion_thread = ConversionThread(folder_path, self.converter)
            self.conversion_thread.progress_signal.connect(self.update_progress)
            self.conversion_thread.log_signal.connect(self.log_message)
            self.conversion_thread.error_signal.connect(lambda e: self.show_error("转换错误", e))
            self.conversion_thread.finished_signal.connect(self.conversion_finished)
            self.conversion_thread.start()
            
        except Exception as e:
            self.show_error("启动转换失败", str(e))
            self.start_button.setEnabled(True)
            self.cancel_button.setEnabled(False)
            
    def conversion_finished(self):
        """转换完成的处理"""
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.log_message("转换完成！")
            
    def cancel_conversion(self):
        """取消转换"""
        try:
            if hasattr(self, 'conversion_thread') and self.conversion_thread.isRunning():
                self.converter.cancel_conversion()
                self.log_message("正在取消转换...")
                self.conversion_thread.wait()
                self.start_button.setEnabled(True)
                self.cancel_button.setEnabled(False)
        except Exception as e:
            self.show_error("取消转换失败", str(e)) 