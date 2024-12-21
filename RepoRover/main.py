import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
import os
from github import Github
from github import RateLimitExceededException
import requests
from PIL import Image
import threading
import re
from urllib.parse import urlparse
import time

class RepoRoverApp:
    def __init__(self):
        self.app = ctk.CTk()
        self.app.title("RepoRover - GitHub文件下载工具")
        self.app.geometry("800x600")
        
        # 设置主题
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # 初始化状态变量
        self.is_downloading = False
        self.total_files = 0
        self.downloaded_files = 0
        
        self.setup_ui()
        
    def setup_ui(self):
        # 创建主框架
        self.main_frame = ctk.CTkFrame(self.app)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 仓库URL输入
        self.url_label = ctk.CTkLabel(self.main_frame, text="GitHub仓库URL:")
        self.url_label.pack(pady=(0, 5), anchor="w")
        self.url_entry = ctk.CTkEntry(self.main_frame, width=600)
        self.url_entry.pack(pady=(0, 15), fill="x")
        
        # 文件后缀输入
        self.suffix_label = ctk.CTkLabel(self.main_frame, text="文件后缀 (用逗号分隔，如: .py,.js,.md):")
        self.suffix_label.pack(pady=(0, 5), anchor="w")
        self.suffix_entry = ctk.CTkEntry(self.main_frame, width=600)
        self.suffix_entry.pack(pady=(0, 15), fill="x")
        
        # 输出路径选择
        self.path_frame = ctk.CTkFrame(self.main_frame)
        self.path_frame.pack(fill="x", pady=(0, 15))
        
        self.path_label = ctk.CTkLabel(self.path_frame, text="输出路径:")
        self.path_label.pack(side="left", padx=(0, 10))
        
        self.path_entry = ctk.CTkEntry(self.path_frame, width=450)
        self.path_entry.pack(side="left", fill="x", expand=True)
        
        self.path_button = ctk.CTkButton(self.path_frame, text="浏览", command=self.select_output_path)
        self.path_button.pack(side="right", padx=(10, 0))
        
        # GitHub Token输入（可选）
        self.token_label = ctk.CTkLabel(self.main_frame, text="GitHub Token (可选，用于访问私有仓库):")
        self.token_label.pack(pady=(0, 5), anchor="w")
        self.token_entry = ctk.CTkEntry(self.main_frame, width=600, show="*")
        self.token_entry.pack(pady=(0, 15), fill="x")
        
        # 进度条
        self.progress_label = ctk.CTkLabel(self.main_frame, text="下载进度:")
        self.progress_label.pack(pady=(0, 5), anchor="w")
        self.progress_bar = ctk.CTkProgressBar(self.main_frame)
        self.progress_bar.pack(fill="x", pady=(0, 15))
        self.progress_bar.set(0)
        
        # 控制按钮
        self.button_frame = ctk.CTkFrame(self.main_frame)
        self.button_frame.pack(fill="x", pady=(0, 15))
        
        self.start_button = ctk.CTkButton(self.button_frame, text="开始下载", command=self.start_download)
        self.start_button.pack(side="left", padx=(0, 10))
        
        self.cancel_button = ctk.CTkButton(self.button_frame, text="取消", command=self.cancel_download)
        self.cancel_button.pack(side="left")
        
        # 日志显示
        self.log_label = ctk.CTkLabel(self.main_frame, text="下载日志:")
        self.log_label.pack(pady=(0, 5), anchor="w")
        
        self.log_text = ctk.CTkTextbox(self.main_frame, height=200)
        self.log_text.pack(fill="both", expand=True)
        
    def update_progress(self):
        """更新进度条"""
        if self.total_files > 0:
            progress = self.downloaded_files / self.total_files
            self.progress_bar.set(progress)
            self.progress_label.configure(text=f"下载进度: {self.downloaded_files}/{self.total_files}")
        
    def count_files(self, repo, contents, suffixes):
        """计算需要下载的文件总数"""
        try:
            for content in contents:
                if not self.is_downloading:
                    return
                    
                if content.type == 'dir':
                    sub_contents = repo.get_contents(content.path)
                    self.count_files(repo, sub_contents, suffixes)
                elif content.type == 'file':
                    file_suffix = os.path.splitext(content.name)[1].lower()
                    if file_suffix in suffixes:
                        self.total_files += 1
                        
        except RateLimitExceededException:
            self.log_message("警告: 已达到GitHub API访问限制，请稍后再试或使用Token")
            raise
        except Exception as e:
            self.log_message(f"计算文件数量时出错: {str(e)}")
            raise

    def process_contents(self, repo, contents, base_path, suffixes):
        """递归处理仓库内容"""
        try:
            for content in contents:
                if not self.is_downloading:
                    return
                
                if content.type == 'dir':
                    self.log_message(f"正在扫描目录: {content.path}")
                    try:
                        sub_contents = repo.get_contents(content.path)
                        self.process_contents(repo, sub_contents, base_path, suffixes)
                    except RateLimitExceededException:
                        self.log_message("警告: 已达到GitHub API访问限制，请稍后再试或使用Token")
                        raise
                    except Exception as e:
                        self.log_message(f"处理目录 {content.path} 时出错: {str(e)}")
                        continue
                    
                elif content.type == 'file':
                    file_suffix = os.path.splitext(content.name)[1].lower()
                    if file_suffix in suffixes:
                        self.log_message(f"正在下载: {content.path}")
                        output_path = os.path.join(base_path, content.path)
                        if self.download_file(content.download_url, output_path):
                            self.downloaded_files += 1
                            self.update_progress()
                            self.log_message(f"下载完成: {content.path}")
                        time.sleep(1)  # 增加延迟以避免触发API限制
                
        except RateLimitExceededException:
            raise
        except Exception as e:
            self.log_message(f"处理内容时出错: {str(e)}")

    def download_files(self):
        """实现文件下载逻辑"""
        try:
            # 获取输入
            url = self.url_entry.get().strip()
            suffixes = [s.strip().lower() for s in self.suffix_entry.get().strip().split(',')]
            output_path = self.path_entry.get().strip()
            token = self.token_entry.get().strip()
            
            # 重置计数器
            self.total_files = 0
            self.downloaded_files = 0
            self.update_progress()
            
            # 解析GitHub URL
            try:
                owner, repo_name = self.parse_github_url(url)
                self.log_message(f"正在访问仓库: {owner}/{repo_name}")
            except ValueError as e:
                self.log_message(f"错误: {str(e)}")
                self.is_downloading = False
                self.start_button.configure(state="normal")
                return
            
            # 创建GitHub客户端
            g = Github(token) if token else Github()
            
            try:
                # 获取仓库
                repo = g.get_repo(f"{owner}/{repo_name}")
                
                # 获取仓库内容
                contents = repo.get_contents("")
                
                # 首先计算总文件数
                self.log_message("正在计算需要下载的文件数量...")
                self.count_files(repo, contents, suffixes)
                self.log_message(f"找到 {self.total_files} 个匹配的文件")
                
                # 重新获取内容并开始下载
                contents = repo.get_contents("")
                self.log_message("开始下载文件...")
                self.process_contents(repo, contents, output_path, suffixes)
                
                if self.is_downloading:
                    self.log_message("下载完成！")
                else:
                    self.log_message("下载已取消。")
                
            except RateLimitExceededException:
                self.log_message("错误: 已达到GitHub API访问限制，请稍后再试或使用Token")
            except Exception as e:
                self.log_message(f"访问仓库失败: {str(e)}")
            
        except Exception as e:
            self.log_message(f"发生错误: {str(e)}")
        
        finally:
            self.is_downloading = False
            self.start_button.configure(state="normal")
            g.close()

    def run(self):
        self.app.mainloop() 