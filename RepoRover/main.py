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
from bs4 import BeautifulSoup
import threading
import re
from urllib.parse import urlparse, urljoin
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
        self.session = requests.Session()
        if token:
            self.session.headers.update({'Authorization': f'token {token}'})
        self.session.headers.update({'User-Agent': 'Mozilla/5.0'})

    def is_file_match(self, filename, patterns):
        """检查文件名是否匹配模式"""
        filename = filename.lower().strip()
        self.log_signal.emit(f"检查文件: {filename}")
        
        # 移除文件名开头的点号（如果有）
        clean_filename = filename[1:] if filename.startswith('.') else filename
        
        for pattern in patterns:
            pattern = pattern.lower().strip()
            # 移除模式开头的点号（如果有）
            clean_pattern = pattern[1:] if pattern.startswith('.') else pattern
            
            self.log_signal.emit(f"对比模式: {pattern} (清理后: {clean_pattern})")
            
            # 完全匹配（同时检查原始名称和清理后的名称）
            if filename == pattern or clean_filename == clean_pattern:
                self.log_signal.emit(f"✓ 文件 {filename} 完全匹配模式 {pattern}")
                return True
            
            # 部分匹配（检查文件名是否包含模式）
            if clean_pattern in clean_filename:
                self.log_signal.emit(f"✓ 文件 {filename} 包含模式 {pattern}")
                return True
            
            # 后缀匹配
            if pattern.startswith('*'):
                suffix = pattern[1:]
            else:
                suffix = pattern
                
            if filename.endswith(suffix) or clean_filename.endswith(clean_pattern):
                self.log_signal.emit(f"✓ 文件 {filename} 后缀匹配模式 {pattern}")
                return True
                
        self.log_signal.emit(f"✗ 文件 {filename} 不匹配任何模式")
        return False

    def scan_github_page(self, url, base_path=''):
        """使用网页解析方式扫描GitHub页面"""
        try:
            self.log_signal.emit(f"\n开始扫描页面: {url}")
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # 输出页面标题
            title = soup.find('title')
            if title:
                self.log_signal.emit(f"\n页面标题: {title.text.strip()}")
            
            files = []
            
            # 直接搜索所有链接
            self.log_signal.emit("\n搜索所有文件链接...")
            all_links = soup.find_all('a', href=True)
            
            for link in all_links:
                if not self.is_running:
                    return []
                
                href = link['href']
                # 确保是完整的仓库内链接
                if not href.startswith('/'):
                    continue
                    
                # 提取文件名和路径
                if '/blob/' in href:
                    # 这是一个文件
                    parts = href.split('/')
                    if len(parts) < 4:  # 确保链接格式正确
                        continue
                        
                    file_name = parts[-1]
                    self.log_signal.emit(f"\n发现文件链接:")
                    self.log_signal.emit(f"- 链接: {href}")
                    self.log_signal.emit(f"- 文件名: {file_name}")
                    
                    # 检查文件名是否匹配
                    if self.is_file_match(file_name, self.suffixes):
                        # 构造下载URL
                        raw_url = f"https://raw.githubusercontent.com{href.replace('/blob/', '/')}"
                        self.log_signal.emit(f"找到匹配文件!")
                        self.log_signal.emit(f"- 文件名: {file_name}")
                        self.log_signal.emit(f"- 下载URL: {raw_url}")
                        
                        # 构造文件路径
                        file_path = '/'.join(parts[4:])  # 跳过 ['', 'owner', 'repo', 'blob', 'branch']
                        full_path = os.path.join(base_path, file_path) if base_path else file_path
                        
                        files.append({
                            'name': file_name,
                            'path': full_path,
                            'download_url': raw_url
                        })
                        self.log_signal.emit(f"✓ 添加匹配文件: {full_path}")
                elif '/tree/' in href:
                    # 这是一个目录
                    self.log_signal.emit(f"\n发现目录链接: {href}")
                    # 构造完整URL并递归扫描
                    full_url = urljoin('https://github.com', href)
                    dir_path = '/'.join(href.split('/')[4:])  # 跳过 ['', 'owner', 'repo', 'tree', 'branch']
                    self.log_signal.emit(f"扫描子目录: {dir_path}")
                    sub_files = self.scan_github_page(full_url, os.path.join(base_path, dir_path) if base_path else dir_path)
                    files.extend(sub_files)
            
            self.log_signal.emit(f"\n本页面找到 {len(files)} 个匹配文件")
            return files
            
        except Exception as e:
            self.log_signal.emit(f"\n扫描页面时出错: {str(e)}")
            return []

    def download_without_api(self, owner, repo):
        """使用网页解析方式下载文件"""
        try:
            repo_url = f"https://github.com/{owner}/{repo}"
            self.log_signal.emit(f"正在扫描仓库: {repo_url}")
            self.log_signal.emit(f"搜索模式: {', '.join(self.suffixes)}")
            
            # 扫描文件
            matching_files = self.scan_github_page(repo_url)
            
            self.total_files = len(matching_files)
            self.log_signal.emit(f"找到 {self.total_files} 个匹配的文件")

            if self.total_files == 0:
                self.error_signal.emit(
                    "没有找到文件",
                    f"在仓库中没有找到匹配的文件。\n当前搜索模式: {', '.join(self.suffixes)}\n" +
                    "请检查文件名或后缀是否正确。\n" +
                    "注意：如果文件在子目录中，程序会自动搜索。"
                )
                return

            # 下载文件
            successful_downloads = 0
            for file_info in matching_files:
                if not self.is_running:
                    return

                file_path = file_info['path']
                download_url = file_info['download_url']
                output_path = os.path.join(self.output_path, file_path)

                self.log_signal.emit(f"正在下载: {file_path}")
                
                try:
                    # 使用流式下载
                    response = self.session.get(download_url, stream=True)
                    response.raise_for_status()
                    
                    # 确保目标目录存在
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    
                    # 写入文件
                    with open(output_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if not self.is_running:
                                return
                            if chunk:
                                f.write(chunk)
                    
                    successful_downloads += 1
                    self.downloaded_files = successful_downloads
                    self.progress_signal.emit(self.downloaded_files, self.total_files)
                    self.log_signal.emit(f"下载完成: {file_path}")
                    
                except Exception as e:
                    self.log_signal.emit(f"下载文件 {file_path} 失败: {str(e)}")
                    continue

                # 添加小延迟以避免触发限制
                time.sleep(0.5)

            # 确保进度条显示100%
            if successful_downloads == self.total_files:
                self.progress_signal.emit(self.total_files, self.total_files)
                self.log_signal.emit("所有文件下载完成！")
            else:
                self.log_signal.emit(f"下载完成，成功: {successful_downloads}/{self.total_files}")

        except Exception as e:
            self.error_signal.emit("下载错误", f"下载过程中出错: {str(e)}")

    def run(self):
        try:
            # 解析GitHub URL
            owner, repo_name = self.parse_github_url(self.url)
            self.log_signal.emit(f"正在访问仓库: {owner}/{repo_name}")

            if not self.use_api:
                # 使用网页解析模式
                self.download_without_api(owner, repo_name)
            else:
                # 使用GitHub API模式
                self.g = Github(self.token) if self.token else Github()
                if not self.check_rate_limit():
                    return
                # ... 原有的API下载代码 ...

            if self.is_running:
                if self.downloaded_files > 0:
                    # 确保进度条显示100%
                    if self.downloaded_files == self.total_files:
                        self.progress_signal.emit(self.total_files, self.total_files)
                    self.log_signal.emit("下载完成！")
            else:
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
        
        # 库URL输入
        url_label = QLabel("GitHub仓库URL:")
        self.url_input = QLineEdit()
        layout.addWidget(url_label)
        layout.addWidget(self.url_input)
        
        # 文件后缀输入
        suffix_label = QLabel("文件后缀或完整文件名 (用逗号分隔，如: .py,.js,.md 或 .cursorrules):")
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
            self.log_message("错误: 请���入GitHub仓库URL")
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