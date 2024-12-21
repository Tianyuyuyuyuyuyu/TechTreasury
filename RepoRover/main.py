import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
import os
from github import Github
import requests
from PIL import Image
import threading
import re
from urllib.parse import urlparse

class RepoRoverApp:
    def __init__(self):
        self.app = ctk.CTk()
        self.app.title("RepoRover - GitHub文件下载工具")
        self.app.geometry("800x600")
        
        # 设置主题
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
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
        
        # 初始化下载状态
        self.is_downloading = False
        
    def select_output_path(self):
        path = filedialog.askdirectory()
        if path:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, path)
            
    def log_message(self, message):
        self.log_text.insert("end", f"{message}\n")
        self.log_text.see("end")
        
    def validate_inputs(self):
        # 验证仓库URL
        url = self.url_entry.get().strip()
        if not url:
            self.log_message("错误: 请输入GitHub仓库URL")
            return False
            
        # 验证文件后缀
        suffixes = self.suffix_entry.get().strip()
        if not suffixes:
            self.log_message("错误: 请输入至少一个文件后缀")
            return False
            
        # 验证输出路径
        output_path = self.path_entry.get().strip()
        if not output_path:
            self.log_message("错误: 请选择输出路径")
            return False
            
        return True
        
    def start_download(self):
        if not self.validate_inputs():
            return
            
        if self.is_downloading:
            self.log_message("警告: 下载任务正在进行中")
            return
            
        self.is_downloading = True
        self.start_button.configure(state="disabled")
        
        # 在新线程中启动下载
        download_thread = threading.Thread(target=self.download_files)
        download_thread.start()
        
    def cancel_download(self):
        if self.is_downloading:
            self.is_downloading = False
            self.log_message("正在取消下载...")
            self.start_button.configure(state="normal")
            
    def download_files(self):
        # TODO: 实现文件下载逻辑
        self.log_message("开始下载文件...")
        # 这里将实现实际的下载逻辑
        
    def run(self):
        self.app.mainloop()

if __name__ == "__main__":
    app = RepoRoverApp()
    app.run() 