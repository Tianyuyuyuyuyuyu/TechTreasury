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
        if not filename or not patterns:
            return False
            
        # 清理和标准化文件名和模式
        filename = filename.strip()
        patterns = [p.strip() for p in patterns if p and p.strip()]
        
        self.log_signal.emit(f"检查文件: {filename}")
        self.log_signal.emit(f"匹配模式: {patterns}")
        
        for pattern in patterns:
            # 1. 完整文件名匹配
            if pattern == filename:
                self.log_signal.emit(f"✓ 完整文件名匹配: {filename} == {pattern}")
                return True
                
            # 2. 以点号开头的模式（作为文件扩展名）
            if pattern.startswith('.'):
                # 检查文件扩展名
                if filename.lower().endswith(pattern.lower()):
                    self.log_signal.emit(f"✓ 扩展名匹配: {filename} 以 {pattern} 结尾")
                    return True
                    
            # 3. 不以点号开头的模式
            else:
                # 如果模式包含点号，作为完整文件名匹配
                if '.' in pattern:
                    if filename.lower() == pattern.lower():
                        self.log_signal.emit(f"✓ 完整文件名匹配（不区分大小写）: {filename} == {pattern}")
                        return True
                # 否则作为扩展名匹配（自动添加点号）
                else:
                    if filename.lower().endswith(f".{pattern.lower()}"):
                        self.log_signal.emit(f"✓ 扩展名匹配（添加点号）: {filename} 以 .{pattern} 结尾")
                        return True
        
        self.log_signal.emit(f"✗ 文件 {filename} 不匹配任何模式")
        return False

    def parse_file_path(self, href):
        """解析文件路径"""
        try:
            parts = href.split('/')
            # 查找关键部分的索引
            blob_index = -1
            for i, part in enumerate(parts):
                if part == 'blob':
                    blob_index = i
                    break
                    
            if blob_index == -1 or blob_index + 2 >= len(parts):
                return None
                
            # 获取从分支名之后到文件名的所有部
            path_parts = parts[blob_index + 2:]
            return '/'.join(path_parts)
            
        except Exception as e:
            self.log_signal.emit(f"解析文件路径出错: {str(e)}")
            return None

    def scan_github_page(self, url, scanned_urls=None):
        """使用网页解析方式扫描GitHub页面"""
        try:
            # 初始化已扫描URL集合
            if scanned_urls is None:
                scanned_urls = set()
            
            # 如果URL已经扫描过，直接返回
            if url in scanned_urls:
                self.log_signal.emit(f"跳过已扫描的页面: {url}")
                return []
                
            # 添加到已扫描集合
            scanned_urls.add(url)
            
            self.log_signal.emit(f"\n开始扫描页面: {url}")
            
            # 获取页面内容
            response = self.session.get(url)
            response.raise_for_status()
            
            # 记录响应信息
            self.log_signal.emit(f"页面响应状态码: {response.status_code}")
            self.log_signal.emit(f"页面内容预览:\n{response.text[:500]}")
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            files = []
            processed_files = set()
            
            # 查找所有可能的文件和目录链接
            all_links = []
            
            # 1. 查找新版GitHub界面的链接
            rows = soup.select('div[role="row"]')
            for row in rows:
                link = row.select_one('a[role="rowheader"]')
                if link and link.get('href'):
                    all_links.append(link)
                    
            # 2. 查找文件列表中的链接
            list_links = soup.select('div.Box-row a')
            all_links.extend(list_links)
            
            # 3. 查找传统布局中的链接
            nav_links = soup.select('div.js-navigation-item a')
            all_links.extend(nav_links)
            
            # 4. 查找文件浏览器中的链接
            content_links = soup.select('td.content a')
            all_links.extend(content_links)
            
            # 5. 查找目录树中的链接
            tree_links = soup.select('div.js-details-container a')
            all_links.extend(tree_links)
            
            # 6. 查找所有可能的文件和目录链接
            all_possible_links = soup.select('a[href*="/blob/"], a[href*="/tree/"]')
            all_links.extend(all_possible_links)
            
            # 去重链接
            unique_links = []
            seen_hrefs = set()
            for link in all_links:
                href = link.get('href', '')
                if href and href not in seen_hrefs and ('/blob/' in href or '/tree/' in href):
                    seen_hrefs.add(href)
                    unique_links.append(link)
            
            # 分类处理链接
            file_links = []
            dir_links = []
            
            for link in unique_links:
                if not self.is_running:
                    return []
                    
                href = link['href']
                if not href.startswith('/'):
                    continue
                
                # 规范化URL
                if href.startswith('http'):
                    parsed = urlparse(href)
                    href = parsed.path
                
                # 分类链接
                parts = [p for p in href.split('/') if p]
                if len(parts) >= 3:  # 至少需要: owner/repo/...
                    if '/blob/' in href:
                        file_links.append((link, href, parts))
                    elif '/tree/' in href:
                        dir_links.append((link, href, parts))
            
            self.log_signal.emit(f"找到 {len(file_links)} 个文件链接")
            self.log_signal.emit(f"找到 {len(dir_links)} 个目录链接")
            
            # 处理文件
            for link, href, parts in file_links:
                if not self.is_running:
                    return []
                
                try:
                    # 提取文件信息
                    file_name = parts[-1]
                    
                    # 获取相对路径
                    blob_index = parts.index('blob')
                    file_path = '/'.join(parts[blob_index + 2:])
                    
                    # 如果文件已处理过，跳过
                    if file_path in processed_files:
                        continue
                    processed_files.add(file_path)
                    
                    self.log_signal.emit(f"\n发现文件:")
                    self.log_signal.emit(f"- 名称: {file_name}")
                    self.log_signal.emit(f"- 路径: {file_path}")
                    
                    # 检查文件名是否匹配
                    if self.is_file_match(file_name, self.suffixes):
                        # 构造下载URL
                        raw_url = f"https://raw.githubusercontent.com{href.replace('/blob/', '/')}"
                        self.log_signal.emit(f"找到匹配文件!")
                        self.log_signal.emit(f"- 下载URL: {raw_url}")
                        
                        files.append({
                            'name': file_name,
                            'path': file_path,
                            'download_url': raw_url
                        })
                        self.log_signal.emit(f"✓ 添加匹配文件: {file_path}")
                        
                except Exception as e:
                    self.log_signal.emit(f"处理文件链接时出错: {str(e)}")
                    continue
            
            # 处理目录
            for link, href, parts in dir_links:
                if not self.is_running:
                    return []
                
                try:
                    # 获取目录路径
                    tree_index = parts.index('tree')
                    dir_path = '/'.join(parts[tree_index + 2:])
                    
                    self.log_signal.emit(f"\n扫描子目录: {dir_path}")
                    
                    # 构造完整URL并递归扫描
                    full_url = urljoin('https://github.com', href)
                    sub_files = self.scan_github_page(full_url, scanned_urls)
                    files.extend(sub_files)
                    
                except Exception as e:
                    self.log_signal.emit(f"处理目录链接时出错: {str(e)}")
                    continue
            
            # 检查是否有分页
            pagination_links = soup.select('a[href*="?after="]')
            for link in pagination_links:
                if not self.is_running:
                    return files
                
                next_page_url = urljoin('https://github.com', link['href'])
                if next_page_url not in scanned_urls:
                    self.log_signal.emit(f"\n扫描下一页: {next_page_url}")
                    next_page_files = self.scan_github_page(next_page_url, scanned_urls)
                    files.extend(next_page_files)
            
            self.log_signal.emit(f"\n本页面找到 {len(files)} 个匹配文件")
            return files
            
        except Exception as e:
            self.log_signal.emit(f"\n扫描页面时出错: {str(e)}")
            if hasattr(e, 'response'):
                self.log_signal.emit(f"响应状态码: {e.response.status_code}")
                self.log_signal.emit(f"响应内容: {e.response.text[:1000]}")
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
                    "请检查文件名或后缀是否正确\n" +
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
                
                # 只使用文件名，不使用完整路径
                file_name = os.path.basename(file_path)
                output_path = os.path.join(self.output_path, file_name)
                
                # 如果文件已存在，添加序号
                base_name, ext = os.path.splitext(file_name)
                counter = 1
                while os.path.exists(output_path):
                    new_name = f"{base_name}_{counter}{ext}"
                    output_path = os.path.join(self.output_path, new_name)
                    counter += 1

                self.log_signal.emit(f"正在下载: {file_path} -> {os.path.basename(output_path)}")
                
                try:
                    # 使用流式下载
                    response = self.session.get(download_url, stream=True)
                    response.raise_for_status()
                    
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
                    self.log_signal.emit(f"下载完成: {os.path.basename(output_path)}")
                    
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

    def download_file(self, url, output_path):
        """下载单个文件"""
        try:
            headers = {}
            if self.token:
                headers['Authorization'] = f'token {self.token}'
            
            response = requests.get(url, headers=headers, stream=True)
            response.raise_for_status()
            
            # 只使用文件名，不使用完整路径
            file_name = os.path.basename(output_path)
            new_output_path = os.path.join(self.output_path, file_name)
            
            # 如果文件已存在，添加序号
            base_name, ext = os.path.splitext(file_name)
            counter = 1
            while os.path.exists(new_output_path):
                new_name = f"{base_name}_{counter}{ext}"
                new_output_path = os.path.join(self.output_path, new_name)
                counter += 1
            
            with open(new_output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if not self.is_running:
                        return False
                    if chunk:
                        f.write(chunk)
            return True
            
        except Exception as e:
            self.log_signal.emit(f"下载文件失败: {str(e)}")
            return False

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
                        time.sleep(1)  # 加延迟以避免触发API限制
                
        except RateLimitExceededException:
            raise
        except Exception as e:
            self.log_signal.emit(f"处理内容时出错: {str(e)}")

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
        
        # 库URL输
        url_label = QLabel("GitHub仓库URL:")
        self.url_input = QLineEdit()
        layout.addWidget(url_label)
        layout.addWidget(self.url_input)
        
        # 文件后缀输入
        suffix_label = QLabel("文件后缀或完整文件名 (用逗号隔，如: .py,.js,.md 或 .cursorrules):")
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