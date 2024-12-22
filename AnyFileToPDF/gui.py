import sys
import os
import logging
import traceback
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QPushButton, QProgressBar, QTextEdit, QLabel,
                            QMessageBox, QFrame, QTreeWidget, QTreeWidgetItem)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QPalette, QColor, QIcon
from converter import PDFConverter

class DropArea(QFrame):
    """可拖放的区域"""
    dropped = pyqtSignal(list)
    
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setMinimumHeight(80)
        self.setStyleSheet("""
            QFrame {
                border: 2px dashed #999999;
                border-radius: 10px;
                background-color: white;
                padding: 10px;
            }
            QFrame:hover {
                border-color: #4a90e2;
                background-color: #f8f9fa;
            }
        """)
        
        # 创建布局
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(4)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # 添加主标题
        title_label = QLabel("单击上传或拖放")
        title_label.setStyleSheet("""
            color: #333333;
            font-size: 14px;
            font-weight: bold;
        """)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 添加支持的格式说明
        format_label = QLabel("支持文本文件、csv、电子表格、音频文件等！")
        format_label.setStyleSheet("""
            color: #666666;
            font-size: 12px;
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
                    padding: 10px;
                }
            """)
            
    def dragLeaveEvent(self, event):
        """拖出文件时的处理"""
        self.setStyleSheet("""
            QFrame {
                border: 2px dashed #999999;
                border-radius: 10px;
                background-color: white;
                padding: 10px;
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
                border: 2px dashed #999999;
                border-radius: 10px;
                background-color: white;
                padding: 10px;
            }
            QFrame:hover {
                border-color: #4a90e2;
                background-color: #f8f9fa;
            }
        """)
        
        urls = event.mimeData().urls()
        if urls:
            paths = []
            for url in urls:
                path = url.toLocalFile()
                if os.path.exists(path):
                    paths.append(path)
            
            if paths:
                self.dropped.emit(paths)
            else:
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setText("请选择有效的文件或文件夹！")
                msg_box.setWindowTitle("警告")
                msg_box.setStyleSheet("""
                    QMessageBox {
                        background-color: white;
                    }
                    QMessageBox QLabel {
                        color: #333333;
                        font-size: 13px;
                        padding: 5px;
                    }
                    QMessageBox QPushButton {
                        background-color: #4a90e2;
                        color: white;
                        border: none;
                        border-radius: 3px;
                        padding: 5px 15px;
                        font-size: 12px;
                    }
                    QMessageBox QPushButton:hover {
                        background-color: #357abd;
                    }
                """)
                msg_box.setButtonText(QMessageBox.Ok, "确定")
                msg_box.exec_()
                
    def mousePressEvent(self, event):
        """点击时的处理"""
        from PyQt5.QtWidgets import QFileDialog
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "选择文件",
            "",
            "所有文件 (*.*)"
        )
        if paths:
            self.dropped.emit(paths)

class FileTreeWidget(QTreeWidget):
    """文件树控件"""
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(150)
        self.setHeaderHidden(True)  # 隐藏表头
        self.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #cccccc;
                border-radius: 5px;
                background-color: white;
                padding: 5px;
                show-decoration-selected: 1;
            }
            QTreeWidget::item {
                padding: 5px;
                color: #333333;
            }
            QTreeWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
            QTreeWidget::item:hover {
                background-color: #f5f5f5;
            }
        """)
        self.setIndentation(20)  # 设置缩进
        self.setSelectionMode(QTreeWidget.ExtendedSelection)
        self.setVerticalScrollMode(QTreeWidget.ScrollPerPixel)  # 平滑滚动
        self.setAnimated(True)  # 启用动画效果
        
        # 连接点击信号
        self.itemClicked.connect(self.handle_item_clicked)
        # 连接展开信号
        self.itemExpanded.connect(self.handle_item_expanded)
        # 连接折叠信号
        self.itemCollapsed.connect(self.handle_item_collapsed)
        
    def handle_item_clicked(self, item, column):
        """处理项目点击事件"""
        # 如果点击的是文件夹（有子项的项目）
        if item.childCount() > 0:
            # 切换展开/折叠状态
            item.setExpanded(not item.isExpanded())
            
    def handle_item_expanded(self, item):
        """处理项目展开事件"""
        # 计算需要显示的区域
        rect = self.visualItemRect(item)
        # 确保展开的项目可见
        self.scrollTo(self.indexFromItem(item), QTreeWidget.PositionAtTop)
        # 等待一小段时间，让展开动画完成
        QTimer.singleShot(100, lambda: self.ensure_children_visible(item))
        
    def handle_item_collapsed(self, item):
        """处理项目折叠事件"""
        # 确保折叠后的项目可见
        self.scrollTo(self.indexFromItem(item))
        
    def ensure_children_visible(self, item):
        """确保子项目可见"""
        # 获取最后一个子项
        if item.childCount() > 0:
            last_child = item.child(item.childCount() - 1)
            # 计算需要显示的区域
            rect = self.visualItemRect(last_child)
            # 如果最后一个子项不在可见区域内，滚动到合适位置
            viewport_height = self.viewport().height()
            if rect.bottom() > viewport_height:
                self.scrollTo(self.indexFromItem(last_child), QTreeWidget.PositionAtBottom)
                
    def mousePressEvent(self, event):
        """处理鼠标点击事件"""
        item = self.itemAt(event.pos())
        if not item:
            # 如果点击空白区域，取消所有选择
            self.clearSelection()
        super().mousePressEvent(event)
        
    def add_path(self, path):
        """添加文件或文件夹到树中"""
        if os.path.exists(path):
            item = QTreeWidgetItem()
            item.setData(0, Qt.UserRole, path)  # 存储完整路径
            name = os.path.basename(path)
            
            if os.path.isdir(path):
                item.setText(0, "📁 " + name)
                self.add_folder_contents(item, path)
                item.setExpanded(True)  # 默认展开文件夹
            else:
                item.setText(0, "📄 " + name)
            
            self.addTopLevelItem(item)
            # 确保新添加的项目可见
            self.scrollToItem(item)
            return item
            
    def add_folder_contents(self, parent_item, folder_path):
        """递归添加文件夹内容"""
        try:
            for entry in os.scandir(folder_path):
                child = QTreeWidgetItem(parent_item)
                child.setData(0, Qt.UserRole, entry.path)  # 存储完整路径
                
                if entry.is_dir():
                    child.setText(0, "📁 " + entry.name)
                    self.add_folder_contents(child, entry.path)
                else:
                    child.setText(0, "📄 " + entry.name)
        except Exception as e:
            print(f"Error reading folder {folder_path}: {str(e)}")
            
    def get_selected_paths(self):
        """获取所有选中项的路径"""
        paths = []
        for item in self.selectedItems():
            path = item.data(0, Qt.UserRole)
            if os.path.exists(path):
                paths.append(path)
        return paths

class ConversionThread(QThread):
    """转换线程"""
    progress_signal = pyqtSignal(float)
    log_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    
    def __init__(self, file_paths, converter):
        super().__init__()
        self.file_paths = file_paths
        self.converter = converter
        
    def run(self):
        try:
            total_files = len(self.file_paths)
            converted_count = 0
            
            # 创建输出目录
            first_file_dir = os.path.dirname(self.file_paths[0])
            output_dir = os.path.join(first_file_dir, 'outputsPDF')
            os.makedirs(output_dir, exist_ok=True)
            
            for index, file_path in enumerate(self.file_paths, 1):
                if self.converter.cancel_flag:
                    self.log_signal.emit("转换已取消！")
                    break
                    
                try:
                    # 获取文件扩展名
                    _, ext = os.path.splitext(file_path)
                    ext = ext.lower()
                    
                    # 创建输出文件路径
                    rel_path = os.path.relpath(file_path, first_file_dir)
                    output_path = os.path.join(output_dir, rel_path + '.pdf')
                    
                    # 确保输出目录存在
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    
                    # 获取对应的转换方法
                    converter_method = self.converter.supported_extensions.get(ext)
                    
                    if converter_method:
                        # 使用对应的转换器
                        if converter_method(file_path, output_path):
                            converted_count += 1
                            self.log_signal.emit(f"成功转换 ({index}/{total_files}): {rel_path}")
                        else:
                            self.log_signal.emit(f"转换失败 ({index}/{total_files}): {rel_path}")
                    else:
                        # 尝试作为文本文件处理
                        self.log_signal.emit(f"尝试读取文件内容 ({index}/{total_files}): {rel_path}")
                        if self.converter.convert_unknown_file(file_path, output_path):
                            converted_count += 1
                            self.log_signal.emit(f"成功转换为文本 ({index}/{total_files}): {rel_path}")
                        else:
                            self.log_signal.emit(f"无法转换文件 ({index}/{total_files}): {rel_path}")
                            
                except Exception as e:
                    self.log_signal.emit(f"处理文件失败 ({index}/{total_files}): {rel_path} - {str(e)}")
                    continue
                    
                # 更新进度
                progress = (index / total_files) * 100
                self.progress_signal.emit(progress)
                
            # 转换完成
            self.log_signal.emit(f"转换完成！共转换 {converted_count}/{total_files} 个文件")
            self.finished_signal.emit()
            
        except Exception as e:
            self.error_signal.emit(str(e))

class PDFConverterGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.converter = PDFConverter()
        self.selected_paths = []
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
            self.setMinimumSize(800, 500)
            
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
            layout.setContentsMargins(40, 20, 40, 20)
            layout.setSpacing(15)
            
            # 添加拖放区域
            self.drop_area = DropArea()
            self.drop_area.dropped.connect(self.handle_folder_selected)
            layout.addWidget(self.drop_area)
            
            # 添加文件列表区域
            files_header = QHBoxLayout()
            
            files_label = QLabel("已选择的文件")
            files_label.setStyleSheet("""
                color: #333333;
                font-weight: bold;
                font-size: 14px;
                margin-top: 10px;
            """)
            files_header.addWidget(files_label)
            
            files_header.addStretch()
            
            # 添加展开/折叠按钮
            expand_button = QPushButton("全部展开")
            expand_button.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #4a90e2;
                    border: none;
                    padding: 4px 8px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    color: #357abd;
                    text-decoration: underline;
                }
            """)
            expand_button.clicked.connect(lambda: self.file_tree.expandAll())
            files_header.addWidget(expand_button)
            
            collapse_button = QPushButton("全部折叠")
            collapse_button.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #4a90e2;
                    border: none;
                    padding: 4px 8px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    color: #357abd;
                    text-decoration: underline;
                }
            """)
            collapse_button.clicked.connect(lambda: self.file_tree.collapseAll())
            files_header.addWidget(collapse_button)
            
            layout.addLayout(files_header)
            
            self.file_tree = FileTreeWidget()
            layout.addWidget(self.file_tree)
            
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
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setText(message)
        msg_box.setWindowTitle(title)
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: white;
            }
            QMessageBox QLabel {
                color: #333333;
                font-size: 13px;
                padding: 5px;
            }
            QMessageBox QPushButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 5px 15px;
                font-size: 12px;
            }
            QMessageBox QPushButton:hover {
                background-color: #357abd;
            }
        """)
        # 移除默认按钮文本的 & 符号
        msg_box.setButtonText(QMessageBox.Ok, "确定")
        msg_box.exec_()
        
    def handle_folder_selected(self, paths):
        """处理选中的文件或文件夹"""
        try:
            self.file_tree.clear()  # 清空现有列表
            
            for path in paths:
                if os.path.exists(path):
                    self.file_tree.add_path(path)
                    self.log_message(f"已添加: {path}")
            
            # 获取所有文件路径（包括子文件夹中的文件）
            self.selected_paths = self.get_all_file_paths(paths)
            
            if self.selected_paths:
                self.start_button.setEnabled(True)
            else:
                self.show_error("错误", "所选路径中没有可转换的文件！")
        except Exception as e:
            self.show_error("选择文件失败", str(e))
            
    def get_all_file_paths(self, paths):
        """获取所有文件路径，包括子文件夹中的文件"""
        all_files = []
        for path in paths:
            if os.path.isfile(path):
                all_files.append(path)
            elif os.path.isdir(path):
                for root, _, files in os.walk(path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        all_files.append(file_path)
        return all_files
        
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
            # 获取当前选中的文件
            selected_paths = self.file_tree.get_selected_paths()
            if selected_paths:
                self.selected_paths = self.get_all_file_paths(selected_paths)
            
            if not self.selected_paths:
                self.show_error("错误", "请选择要转换的文件！")
                return
                
            self.start_button.setEnabled(False)
            self.cancel_button.setEnabled(True)
            self.drop_area.setEnabled(False)
            self.file_tree.setEnabled(False)  # 禁用文件树
            
            # 创建输出目录
            output_dir = os.path.join(os.path.dirname(self.selected_paths[0]), 'outputsPDF')
            os.makedirs(output_dir, exist_ok=True)
            
            # 创建并启动转换线程
            self.conversion_thread = ConversionThread(self.selected_paths, self.converter)
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
            self.file_tree.setEnabled(True)  # 启用文件树
            
    def conversion_finished(self):
        """转换完成的处理"""
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.drop_area.setEnabled(True)
        self.file_tree.setEnabled(True)  # 启用文件树
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
                self.file_tree.setEnabled(True)  # 启用文件树
        except Exception as e:
            self.show_error("取消转换失败", str(e)) 