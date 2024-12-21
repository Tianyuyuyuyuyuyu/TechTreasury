import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                           QTextEdit, QFileDialog, QProgressBar, QMessageBox,
                           QCheckBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import os
from github import Github
from github import RateLimitExceededException, UnknownObjectException, GithubException
import requests
import threading
import re
from urllib.parse import urlparse
import time
from datetime import datetime
import json
import base64

class DownloadThread(QThread):
    progress_signal = pyqtSignal(int, int)
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str, str)

    def __init__(self, url, suffixes, output_path, token, use_api=False):
        super().__init__()
        self.url = url
        self.suffixes = suffixes
        self.output_path = output_path
        self.token = token
        self.use_api = use_api
        self.is_running = True
        self.total_files = 0
        self.downloaded_files = 0
        self.g = None

    def get_raw_content_url(self, owner, repo, path, branch='main'):
        """获取文件的原始内容URL"""
        return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"

    def get_tree_url(self, owner, repo, branch='main'):
        """获取仓库文件树的URL"""
        return f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"

    def download_without_api(self, owner, repo):
        """使用树API直接下载文件"""
        try:
            # 构建请求头
            headers = {'Accept': 'application/vnd.github.v3+json'}
            if self.token:
                headers['Authorization'] = f'token {self.token}'

            # 获取默认分支
            repo_url = f"https://api.github.com/repos/{owner}/{repo}"
            response = requests.get(repo_url, headers=headers)
            response.raise_for_status()
            default_branch = response.json()['default_branch']

            # 获取文件树
            tree_url = self.get_tree_url(owner, repo, default_branch)
            response = requests.get(tree_url, headers=headers)
            response.raise_for_status()
            tree = response.json()

            # 计算匹配文件数量
            matching_files = [item for item in tree['tree'] 
                            if item['type'] == 'blob' and 
                            any(item['path'].lower().endswith(suffix) for suffix in self.suffixes)]
            
            self.total_files = len(matching_files)
            self.log_signal.emit(f"找到 {self.total_files} 个匹配的文件")

            if self.total_files == 0:
                self.error_signal.emit(
                    "没有找到文件",
                    f"在仓库中没有找到匹配的文件。\n当前搜索后缀: {', '.join(self.suffixes)}"
                )
                return

            # 下载文件
            for file_info in matching_files:
                if not self.is_running:
                    return

                file_path = file_info['path']
                raw_url = self.get_raw_content_url(owner, repo, file_path, default_branch)
                output_path = os.path.join(self.output_path, file_path)

                self.log_signal.emit(f"正在下载: {file_path}")
                if self.download_file(raw_url, output_path):
                    self.downloaded_files += 1
                    self.progress_signal.emit(self.downloaded_files, self.total_files)
                    self.log_signal.emit(f"下载完成: {file_path}")

                time.sleep(0.5)  # 添加小延迟

        except requests.exceptions.RequestException as e:
            if e.response and e.response.status_code == 403:
                self.error_signal.emit("访问限制", "访问被拒绝，请检查您的Token是否有效，或等待限制重置。")
            else:
                self.error_signal.emit("下载错误", f"下载文件时出错: {str(e)}")

    def run(self):
        try:
            # 解析GitHub URL
            owner, repo_name = self.parse_github_url(self.url)
            self.log_signal.emit(f"正在访问仓库: {owner}/{repo_name}")

            if not self.use_api:
                # 使用直接下载模式
                self.download_without_api(owner, repo_name)
            else:
                # 使用GitHub API模式
                self.g = Github(self.token) if self.token else Github()
                if not self.check_rate_limit():
                    return
                # ... 原有的API下载代码 ...

            if self.is_running and self.downloaded_files > 0:
                self.log_signal.emit("下载完成！")
            elif not self.is_running:
                self.log_signal.emit("下载已取消。")

        except ValueError as e:
            self.error_signal.emit("URL错误", str(e))
        except Exception as e:
            self.error_signal.emit("错误", f"发生错误: {str(e)}")
        finally:
            if self.g:
                self.g.close()
            self.finished_signal.emit()

    def check_rate_limit(self):
        """检查 API 访问限制"""
        try:
            rate_limit = self.g.get_rate_limit()
            core_rate = rate_limit.core
            remaining = core_rate.remaining
            reset_time = core_rate.reset.replace(tzinfo=None)
            now = datetime.utcnow()
            
            if remaining == 0:
                wait_time = (reset_time - now).total_seconds()
                if wait_time > 0:
                    self.error_signal.emit(
                        "API 限制",
                        f"已达到 GitHub API 访问限制。\n"
                        f"剩余配额: {remaining}\n"
                        f"重置时间: {reset_time.strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
                        f"需要等待: {int(wait_time/60)} 分钟"
                    )
                    return False
            else:
                self.log_signal.emit(f"API 配额剩余: {remaining}")
            return True
            
        except Exception as e:
            self.log_signal.emit(f"检查 API 限制时出错: {str(e)}")
            return True

    def parse_github_url(self, url):
        try:
            url = url.rstrip('/')
            
            if url.startswith('git@github.com:'):
                path = url.split('git@github.com:')[1]
                owner, repo = path.split('/')
                if repo.endswith('.git'):
                    repo = repo[:-4]
                return owner, repo
            
            parsed = urlparse(url)
            if parsed.netloc != 'github.com':
                raise ValueError("不是有效的GitHub URL")
            
            path_parts = parsed.path.strip('/').split('/')
            if len(path_parts) < 2:
                raise ValueError("URL格式不正确")
            
            owner, repo = path_parts[:2]
            if repo.endswith('.git'):
                repo = repo[:-4]
            
            return owner, repo
            
        except Exception as e:
            raise ValueError(f"无法解析GitHub URL: {str(e)}")

    def count_files(self, repo, contents):
        try:
            for content in contents:
                if not self.is_running:
                    return
                    
                if content.type == 'dir':
                    sub_contents = repo.get_contents(content.path)
                    self.count_files(repo, sub_contents)
                elif content.type == 'file':
                    file_suffix = os.path.splitext(content.name)[1].lower()
                    if file_suffix in self.suffixes:
                        self.total_files += 1
                        
        except RateLimitExceededException:
            raise
        except Exception as e:
            self.log_signal.emit(f"计算文件数量时出错: {str(e)}")
            raise

    def process_contents(self, repo, contents):
        try:
            for content in contents:
                if not self.is_running:
                    return
                
                if content.type == 'dir':
                    self.log_signal.emit(f"正在扫描目录: {content.path}")
                    try:
                        sub_contents = repo.get_contents(content.path)
                        self.process_contents(repo, sub_contents)
                    except RateLimitExceededException:
                        raise
                    except Exception as e:
                        self.log_signal.emit(f"处理目录 {content.path} 时出错: {str(e)}")
                        continue
                    
                elif content.type == 'file':
                    file_suffix = os.path.splitext(content.name)[1].lower()
                    if file_suffix in self.suffixes:
                        self.log_signal.emit(f"正在下载: {content.path}")
                        output_path = os.path.join(self.output_path, content.path)
                        if self.download_file(content.download_url, output_path):
                            self.downloaded_files += 1
                            self.progress_signal.emit(self.downloaded_files, self.total_files)
                            self.log_signal.emit(f"下载完成: {content.path}")
                        time.sleep(1)  # 增加延迟以避免触发API限制
                
        except RateLimitExceededException:
            raise
        except Exception as e:
            self.log_signal.emit(f"处理内容时出错: {str(e)}")

    def download_file(self, url, output_path):
        try:
            headers = {}
            if self.token:
                headers['Authorization'] = f'token {self.token}'
            
            response = requests.get(url, headers=headers, stream=True)
            response.raise_for_status()
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if not self.is_running:
                        return False
                    if chunk:
                        f.write(chunk)
            return True
            
        except Exception as e:
            self.log_signal.emit(f"下载文件失败: {str(e)}")
            return False

    def stop(self):
        self.is_running = False

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RepoRover - GitHub文件下载工具")
        self.setGeometry(100, 100, 800, 600)
        
        # 创建主窗口部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # 创建布局
        layout = QVBoxLayout()
        
        # 仓库URL输入
        url_label = QLabel("GitHub仓库URL:")
        self.url_input = QLineEdit()
        layout.addWidget(url_label)
        layout.addWidget(self.url_input)
        
        # 文件后缀输入
        suffix_label = QLabel("文件后缀 (用逗号分隔，如: .py,.js,.md):")
        self.suffix_input = QLineEdit()
        layout.addWidget(suffix_label)
        layout.addWidget(self.suffix_input)
        
        # 输出路径选择
        path_layout = QHBoxLayout()
        path_label = QLabel("输出路径:")
        self.path_input = QLineEdit()
        browse_button = QPushButton("浏览")
        browse_button.clicked.connect(self.select_output_path)
        path_layout.addWidget(path_label)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(browse_button)
        layout.addLayout(path_layout)
        
        # GitHub Token输入
        token_label = QLabel("GitHub Token (可选，用于访问私有仓库):")
        self.token_input = QLineEdit()
        self.token_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(token_label)
        layout.addWidget(self.token_input)
        
        # 进度条
        self.progress_label = QLabel("下载进度: 0/0")
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)
        
        # 控制按钮
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("开始下载")
        self.start_button.clicked.connect(self.start_download)
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.cancel_download)
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        # 日志显示
        log_label = QLabel("下载日志:")
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(log_label)
        layout.addWidget(self.log_text)
        
        # 添加下载模式选择
        mode_layout = QHBoxLayout()
        self.api_mode_checkbox = QCheckBox("使用 GitHub API（需要Token，但更准确）")
        self.api_mode_checkbox.setChecked(False)
        mode_layout.addWidget(self.api_mode_checkbox)
        layout.addLayout(mode_layout)
        
        # 设置主布局
        main_widget.setLayout(layout)
        
        # 初始化下载线程
        self.download_thread = None

    def select_output_path(self):
        path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if path:
            self.path_input.setText(path)

    def log_message(self, message):
        self.log_text.append(message)

    def update_progress(self, current, total):
        self.progress_label.setText(f"下载进度: {current}/{total}")
        if total > 0:
            self.progress_bar.setValue(int(current * 100 / total))

    def validate_inputs(self):
        if not self.url_input.text().strip():
            self.log_message("错误: 请输入GitHub仓库URL")
            return False
            
        if not self.suffix_input.text().strip():
            self.log_message("错误: 请输入至少一个文件后缀")
            return False
            
        if not self.path_input.text().strip():
            self.log_message("错误: 请选择输出路径")
            return False
            
        return True

    def show_error(self, title, message):
        """显示错误对话框"""
        QMessageBox.critical(self, title, message)

    def start_download(self):
        if not self.validate_inputs():
            return
            
        if self.download_thread and self.download_thread.isRunning():
            self.log_message("警告: 下载任务正在进行中")
            return
            
        # 获取输入
        url = self.url_input.text().strip()
        suffixes = [s.strip().lower() for s in self.suffix_input.text().strip().split(',')]
        output_path = self.path_input.text().strip()
        token = self.token_input.text().strip()
        use_api = self.api_mode_checkbox.isChecked()
        
        # 重置进度
        self.progress_bar.setValue(0)
        self.progress_label.setText("下载进度: 0/0")
        self.log_text.clear()
        
        # 创建并启动下载线程
        self.download_thread = DownloadThread(url, suffixes, output_path, token, use_api)
        self.download_thread.progress_signal.connect(self.update_progress)
        self.download_thread.log_signal.connect(self.log_message)
        self.download_thread.error_signal.connect(self.show_error)
        self.download_thread.finished_signal.connect(self.download_finished)
        
        self.start_button.setEnabled(False)
        self.download_thread.start()

    def cancel_download(self):
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.stop()
            self.log_message("正在取消下载...")

    def download_finished(self):
        self.start_button.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_()) 