import sys
import os
import logging
import traceback
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QPushButton, QProgressBar, QTextEdit, QLabel,
                            QMessageBox, QFrame)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPalette, QColor
from converter import PDFConverter

class DropArea(QFrame):
    """可拖放的区域"""
    dropped = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setMinimumHeight(120)
        self.setStyleSheet("""
            QFrame {
                border: 2px dashed #999999;
                border-radius: 10px;
                background-color: white;
                padding: 20px;
            }
            QFrame:hover {
                border-color: #4a90e2;
                background-color: #f8f9fa;
            }
        """)
        
        # 创建布局
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(8)
        
        # 添加主标题
        title_label = QLabel("单击上传或拖放")
        title_label.setStyleSheet("""
            color: #333333;
            font-size: 15px;
            font-weight: bold;
        """)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 添加支持的格式说明
        format_label = QLabel("支持文本文件、csv、电子表格、音频文件等！")
        format_label.setStyleSheet("""
            color: #666666;
            font-size: 13px;
        """)
        format_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(format_label)

    def dragEnterEvent(self, event):
        """拖入文件时的处理"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("""
                QFrame {
                    border: 2px dashed #4a90e2;
                    border-radius: 10px;
                    background-color: #f8f9fa;
                    padding: 20px;
                }
            """)
            
    def dragLeaveEvent(self, event):
        """拖出文件时的处理"""
        self.setStyleSheet("""
            QFrame {
                border: 2px dashed #999999;
                border-radius: 10px;
                background-color: white;
                padding: 20px;
            }
            QFrame:hover {
                border-color: #4a90e2;
                background-color: #f8f9fa;
            }
        """)
        
    def dropEvent(self, event):
        """放下文件时的处理"""
        self.setStyleSheet("""
            QFrame {
                border: 2px dashed rgba(255, 255, 255, 0.3);
                border-radius: 10px;
                background-color: #1e1e1e;
                padding: 20px;
            }
            QFrame:hover {
                border-color: rgba(255, 255, 255, 0.5);
                background-color: #2a2a2a;
            }
        """)
        
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if os.path.isdir(path):
                self.dropped.emit(path)
            else:
                QMessageBox.warning(self, "警告", "请选择一个文件夹！")
                
    def mousePressEvent(self, event):
        """点击时的处理"""
        from PyQt5.QtWidgets import QFileDialog
        path = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if path:
            self.dropped.emit(path)

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
            # 设置口属性
            self.setWindowTitle("AnyFileToPDF转换器")
            self.setMinimumSize(800, 600)
            
            # 设置窗口背景色
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #f5f5f5;
                }
                QWidget {
                    background-color: #f5f5f5;
                }
            """)
            
            # 创建中央部件
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            
            # 创建主布局
            layout = QVBoxLayout(central_widget)
            layout.setContentsMargins(40, 40, 40, 40)
            layout.setSpacing(20)
            
            # 添加拖放区域
            self.drop_area = DropArea()
            self.drop_area.dropped.connect(self.handle_folder_selected)
            layout.addWidget(self.drop_area)
            
            # 进度条
            self.progress_bar = QProgressBar()
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setStyleSheet("""
                QProgressBar {
                    border: none;
                    border-radius: 5px;
                    text-align: center;
                    height: 20px;
                    background-color: #e0e0e0;
                    color: #333333;
                }
                QProgressBar::chunk {
                    background-color: #4a90e2;
                    border-radius: 5px;
                }
            """)
            layout.addWidget(self.progress_bar)
            
            # 日志区域
            log_label = QLabel("转换日志")
            log_label.setStyleSheet("""
                color: #333333;
                font-weight: bold;
                font-size: 14px;
            """)
            layout.addWidget(log_label)
            
            self.log_text = QTextEdit()
            self.log_text.setReadOnly(True)
            self.log_text.setStyleSheet("""
                QTextEdit {
                    border: 1px solid #cccccc;
                    border-radius: 5px;
                    padding: 10px;
                    background-color: white;
                    color: #333333;
                }
            """)
            layout.addWidget(self.log_text)
            
            # 按钮区域
            button_layout = QHBoxLayout()
            button_layout.setSpacing(10)
            
            self.start_button = QPushButton("开始转换")
            self.start_button.setStyleSheet("""
                QPushButton {
                    background-color: #4a90e2;
                    color: white;
                    border: none;
                    padding: 8px 24px;
                    border-radius: 5px;
                    font-weight: bold;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #357abd;
                }
                QPushButton:disabled {
                    background-color: #cccccc;
                    color: #666666;
                }
            """)
            self.start_button.clicked.connect(self.start_conversion)
            
            self.cancel_button = QPushButton("取消")
            self.cancel_button.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    color: white;
                    border: none;
                    padding: 8px 24px;
                    border-radius: 5px;
                    font-weight: bold;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #c0392b;
                }
                QPushButton:disabled {
                    background-color: #cccccc;
                    color: #666666;
                }
            """)
            self.cancel_button.clicked.connect(self.cancel_conversion)
            self.cancel_button.setEnabled(False)
            
            button_layout.addStretch()
            button_layout.addWidget(self.start_button)
            button_layout.addWidget(self.cancel_button)
            button_layout.addStretch()
            
            layout.addLayout(button_layout)
            
        except Exception as e:
            self.show_error("界面初始化失败", str(e))
            raise
            
    def show_error(self, title, message):
        """显示错误对话框"""
        QMessageBox.critical(self, title, message)
        
    def handle_folder_selected(self, folder_path):
        """处理选中的文件夹"""
        try:
            if os.path.exists(folder_path):
                self.selected_folder = folder_path
                self.log_message(f"已选择文件夹: {folder_path}")
                self.start_button.setEnabled(True)
            else:
                self.show_error("错误", "所选文件夹不存在！")
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
            if not hasattr(self, 'selected_folder'):
                self.show_error("错误", "请选择要转换的文件夹！")
                return
                
            if not os.path.exists(self.selected_folder):
                self.show_error("错误", "所选文件夹不存在！")
                return
                
            self.start_button.setEnabled(False)
            self.cancel_button.setEnabled(True)
            self.drop_area.setEnabled(False)
            
            # 创建并启动转换线程
            self.conversion_thread = ConversionThread(self.selected_folder, self.converter)
            self.conversion_thread.progress_signal.connect(self.update_progress)
            self.conversion_thread.log_signal.connect(self.log_message)
            self.conversion_thread.error_signal.connect(lambda e: self.show_error("转换错误", e))
            self.conversion_thread.finished_signal.connect(self.conversion_finished)
            self.conversion_thread.start()
            
        except Exception as e:
            self.show_error("启动转换失败", str(e))
            self.start_button.setEnabled(True)
            self.cancel_button.setEnabled(False)
            self.drop_area.setEnabled(True)
            
    def conversion_finished(self):
        """转换完成的处理"""
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.drop_area.setEnabled(True)
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
                self.drop_area.setEnabled(True)
        except Exception as e:
            self.show_error("取消转换失败", str(e)) 