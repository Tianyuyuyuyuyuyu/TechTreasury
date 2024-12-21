import os
import shutil
import ctypes
import sys
from datetime import datetime
import logging
import time
import subprocess
import tkinter as tk
from tkinter import ttk
from threading import Thread

def is_admin():
    """检查程序是否以管理员权限运行"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    """以管理员权限重新启动程序"""
    try:
        if not is_admin():
            # 准备当前脚本的路径
            script = os.path.abspath(sys.argv[0])
            params = ' '.join(sys.argv[1:])
            
            # 如果是 .py 文件，使用 python 执行
            if script.endswith('.py'):
                cmd = f'"{sys.executable}" "{script}"'
            else:
                # 如果是 .exe 文件，直接执行
                cmd = f'"{script}"'
            
            if params:
                cmd = f'{cmd} {params}'
            
            # 请求 UAC 提升
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, cmd, None, 1)
            sys.exit()
        return True
    except Exception as e:
        logging.error(f"请求管理员权限时出错: {str(e)}")
        return False

def setup_logging():
    """设置日志记录"""
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    log_file = os.path.join(log_dir, f'disk_clean_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def get_resource_path(relative_path):
    """获取资源文件的绝对路径"""
    try:
        # PyInstaller创建临时文件夹,将路径存储在_MEIPASS中
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class CleanerGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("吓吓C盘 - 雨雨雨雨雨雨雨雨")
        
        # 设置窗口图标
        try:
            # 获取图标路径
            icon_path = get_resource_path('cleaner.ico')
            
            # 如果图标不存在，先创建
            if not os.path.exists(icon_path):
                try:
                    from create_icon import create_rain_tech_icon
                    icon_path = create_rain_tech_icon()
                except Exception as e:
                    logging.warning(f"创建图标失败: {str(e)}")
            
            # 设置窗口图标
            if icon_path and os.path.exists(icon_path):
                self.root.iconbitmap(default=icon_path)
            else:
                logging.warning("图标文件不存在")
        except Exception as e:
            logging.warning(f"设置图标失败: {str(e)}")
        
        # 设置窗口大小和位置
        window_width = 400
        window_height = 250
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # 创建界面元素
        self.setup_ui()
        
        # 创建清理器实例
        self.cleaner = DiskCleaner(self)
        
        self.current_task = 0
        self.total_tasks = 3
        self.completed_tasks = []
        
    def setup_ui(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 标题标签
        self.title_label = ttk.Label(main_frame, text="准备开始清理...", font=("Microsoft YaHei", 12))
        self.title_label.grid(row=0, column=0, pady=(0, 10))
        
        # 进度条组
        progress_group = ttk.LabelFrame(main_frame, text="清理进度", padding="10")
        progress_group.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        self.progress = ttk.Progressbar(progress_group, length=350, mode='determinate')
        self.progress.grid(row=0, column=0, pady=5)
        
        # 状态组
        self.status_group = ttk.LabelFrame(main_frame, text="当前状态", padding="10")
        self.status_group.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        self.status_label = ttk.Label(self.status_group, text="", wraplength=350)
        self.status_label.grid(row=0, column=0, pady=5)
        
        # 任务结果组（初始隐藏）
        self.result_group = ttk.LabelFrame(main_frame, text="清理结果", padding="10")
        self.result_group.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        self.result_label = ttk.Label(self.result_group, text="", wraplength=350, justify=tk.LEFT)
        self.result_label.grid(row=0, column=0, pady=5)
        self.result_group.grid_remove()  # 初始时隐藏
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, pady=(10, 0))
        
        # 退出按钮
        self.exit_button = ttk.Button(button_frame, text="完成", command=self.root.destroy, width=20)
        self.exit_button.grid(row=0, column=0, pady=5)
        self.exit_button.grid_remove()
        
    def update_status(self, status, detail=""):
        self.title_label['text'] = status
        self.status_label['text'] = detail
        self.root.update()
        
    def show_completion(self, total_cleaned):
        """显示完成信息"""
        self.update_progress(100, False)  # 设置进度条为100%
        self.title_label['text'] = "清理完成！"
        self.status_label['text'] = f"总共释放空间: {total_cleaned}"
        
        # 生成任务执行结果报告
        result_text = "执行的任务：\n\n"
        
        # 显示成功的任务
        for task_name, details in self.completed_tasks:
            result_text += f"✓ {task_name}\n"
            if details:
                result_text += f"   {details}\n"
        
        # 显示失败的任务（如果有）
        if self.cleaner.files_failed > 0:
            result_text += f"\n未能完成的操作：\n"
            result_text += f"• {self.cleaner.files_failed} 个文件无法删除（可能被占用）\n"
        
        # 显示总结
        result_text += f"\n清理统计：\n"
        result_text += f"• 处理文件总数：{self.cleaner.files_processed}\n"
        result_text += f"• 成功删除：{self.cleaner.files_deleted} 个文件\n"
        result_text += f"• 释放空间：{total_cleaned}\n"
        
        # 显示结果
        self.result_group.grid()  # 显示结果组
        self.result_label['text'] = result_text
        
        # 确保按钮显示
        self.exit_button.grid()
        
        # 调整窗口大小以适应所有内容
        self.root.update_idletasks()
        self.root.geometry('')  # 自动调整窗口大小
        
        # 将按钮移到前台
        self.exit_button.lift()
        self.exit_button.focus_set()
        
        # 刷新界面
        self.root.update()
    
    def start_cleaning(self):
        """启动清理进程"""
        # 在新线程中运行清理过程
        Thread(target=self.cleaner.clean_system, daemon=True).start()
    
    def update_progress(self, value, task_progress=True):
        """更新进度条"""
        if task_progress:
            # 计算总体进度：当前任务进度 + 之前任务的进度
            total_progress = (self.current_task * 100 + value) / self.total_tasks
            self.progress['value'] = total_progress
        else:
            # 直接设置进度值（用于最终完成时）
            self.progress['value'] = value
        self.root.update()
    
    def next_task(self):
        """移动到下一个任务"""
        self.current_task += 1
        
    def add_completed_task(self, task_name, details=""):
        """添加已完成的任务到列表"""
        self.completed_tasks.append((task_name, details))

class DiskCleaner:
    def __init__(self, gui):
        self.gui = gui
        self.total_cleaned = 0
        self.task_cleaned = 0  # 添加当前任务的清理空间统计
        self.files_processed = 0
        self.files_deleted = 0
        self.files_failed = 0
        self.locked_patterns = set()
        
    def reset_task_stats(self):
        """重置当前任务的统计"""
        self.task_cleaned = 0
        
    def get_size_format(self, bytes):
        """将字节转换为人类可读的格式"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes < 1024.0:
                return f"{bytes:.2f} {unit}"
            bytes /= 1024.0

    def is_safe_to_delete(self, file_path):
        """检查文件是否安全删除"""
        # 只保护系统关键文件
        unsafe_extensions = {'.sys', '.dll', '.exe'}
        unsafe_patterns = {'windows', 'system32', 'program files'}
        
        file_ext = os.path.splitext(file_path)[1].lower()
        file_path_lower = file_path.lower()
        
        # 检查是否匹配已知的被锁定模式（由于权限问题导致的）
        for pattern in self.locked_patterns:
            if pattern in file_path_lower:
                logging.debug(f"跳过已知被锁定的文件: {file_path}")
                return False
        
        # 只有当文件是系统文件时才禁止除
        if file_ext in unsafe_extensions and any(pattern in file_path_lower for pattern in unsafe_patterns):
            logging.debug(f"跳过系统文件: {file_path}")
            return False
        
        # 其他所有文件都允许删除
        return True

    def try_delete_file(self, file_path, max_retries=2, delay=0.5):
        """尝试删除文件带重试机制"""
        if not self.is_safe_to_delete(file_path):
            self.files_failed += 1
            return False

        for attempt in range(max_retries):
            try:
                if os.path.isfile(file_path):
                    file_size = os.path.getsize(file_path)
                    os.remove(file_path)
                    self.task_cleaned += file_size  # 更新当前任务的清理空间
                    self.files_deleted += 1
                    return True
                return False
            except PermissionError:
                if attempt == max_retries - 1:
                    self.files_failed += 1
                    return False
                time.sleep(delay)
            except Exception as e:
                logging.error(f"删除 {file_path} 时出错: {str(e)}")
                self.files_failed += 1
                return False
        return False

    def clean_temp_folders(self):
        """清理临时文件夹"""
        self.reset_task_stats()  # 重置当前任务统计
        self.gui.update_status("正在清理临时文件", "正在扫描文件...")
        
        # 要清理的临时文件夹列表
        temp_folders = [
            os.environ.get('TEMP'),  # 用户临时文件夹
            os.environ.get('TMP'),   # 系统临时文件夹
            os.path.join(os.environ.get('LOCALAPPDATA'), 'Temp'),  # Local AppData Temp
            os.path.join(os.environ.get('SYSTEMROOT'), 'Temp'),    # Windows Temp
            os.path.join(os.environ.get('SYSTEMROOT'), 'Prefetch') # 预读取文件夹
        ]
        
        files_count = 0
        current_progress = 0
        
        # 遍历每个临时文件夹
        for folder in temp_folders:
            if not folder or not os.path.exists(folder):
                continue
            
            self.gui.update_status("正在清理临时文件", f"正在处理: {folder}")
            
            # 遍历文件夹中的所有文件
            for root, dirs, files in os.walk(folder, topdown=False):
                for name in files:
                    file_path = os.path.join(root, name)
                    self.files_processed += 1
                    
                    # 尝试删除文件
                    if self.try_delete_file(file_path):
                        files_count += 1
                    
                    # 更新进度
                    if files_count % 10 == 0:
                        current_progress = min(90, int((files_count / 1000) * 100))
                        self.gui.update_progress(current_progress)
            
            # 尝试删除空文件夹
            try:
                os.rmdir(root)
            except:
                pass
        
        self.gui.update_progress(100)
        self.gui.add_completed_task("临时文件清理", 
                                  f"释放空间: {self.get_size_format(self.task_cleaned)}")
        self.total_cleaned += self.task_cleaned  # 累加到总清理空间
        self.gui.next_task()

    def check_hibernation_status(self):
        """检查系统休眠状态"""
        try:
            # 方法1：检查 hiberfil.sys 文件
            hibernate_file = os.path.join(os.environ.get('SystemDrive', 'C:'), 'hiberfil.sys')
            file_exists = os.path.exists(hibernate_file)
            
            # 方法2：使用 powercfg 命令查询休眠状态
            result = subprocess.run(['powercfg', '/availablesleepstates'], 
                                 capture_output=True, 
                                 text=True, 
                                 shell=True)
            
            # 更新检测逻辑：检查是否包含"尚未启用休眠"或"Hibernate is not available"
            hibernate_disabled = '尚未启用休眠' in result.stdout or 'Hibernate is not available' in result.stdout
            
            if hibernate_disabled and not file_exists:
                return True, "系统休眠已成功关闭"
            elif file_exists:
                return False, "休眠文件 (hiberfil.sys) 仍然存在"
            elif not hibernate_disabled:
                return False, "系统休眠功能仍然启用"
            
            return True, "系统休眠已关闭"
        except Exception as e:
            return False, f"检查休眠状态时出错: {str(e)}"

    def disable_hibernation(self):
        """关闭系统休眠功能"""
        self.reset_task_stats()  # 重置当前任务统计
        self.gui.update_status("正在关闭系统休眠", "正在执行命令...")
        
        try:
            # 执行关闭休眠的命令
            subprocess.run(['powercfg', '/hibernate', 'off'], 
                         capture_output=True,
                         check=True)
            
            # 检查休眠状态
            success, message = self.check_hibernation_status()
            
            if success:
                # 获取 hiberfil.sys 的大小（如果存在）
                hibernate_file = os.path.join(os.environ.get('SystemDrive', 'C:'), 
                                            'hiberfil.sys')
                if os.path.exists(hibernate_file):
                    try:
                        size = os.path.getsize(hibernate_file)
                        self.task_cleaned += size
                        self.total_cleaned += size
                    except:
                        pass
                
                self.gui.add_completed_task("系统休眠关闭", 
                                          f"释放空间: {self.get_size_format(self.task_cleaned)}")
            else:
                self.gui.add_completed_task("系统休眠关闭", "操作失败")
            
        except subprocess.CalledProcessError as e:
            logging.error(f"关闭休眠失败: {str(e)}")
            self.gui.add_completed_task("系统休眠关闭", "操作失败")
        
        self.gui.next_task()

    def clean_system_storage(self):
        """清理系统存储"""
        self.reset_task_stats()  # 重置当前任务统计
        self.gui.update_status("正在清理系统存储", "正在准备...")
        
        # 要清理的系统文件夹列表，按优先级排序
        system_folders = [
            # 优先清理更新缓存
            os.path.join(os.environ.get('SYSTEMROOT'), 'SoftwareDistribution\\Download'),
            
            # 然后是日志文件
            os.path.join(os.environ.get('SYSTEMROOT'), 'Logs'),
            
            # 最后是其他缓存
            os.path.join(os.environ.get('SYSTEMROOT'), 'Debug'),
            os.path.join(os.environ.get('SYSTEMROOT'), 'Installer\\$PatchCache$')
        ]
        
        # 跳过的文件类型
        skip_extensions = {'.dll', '.exe', '.sys', '.msi', '.cat', '.ini'}
        
        files_count = 0
        current_progress = 0
        
        # 遍历每个系统文件夹
        for folder in system_folders:
            if not folder or not os.path.exists(folder):
                continue
            
            self.gui.update_status("正在清理系统存储", f"正在处理: {folder}")
            
            try:
                # 遍历文件夹中的所有文件
                for root, dirs, files in os.walk(folder, topdown=False):
                    # 跳过某些系统目录
                    if any(skip_dir in root.lower() for skip_dir in ['windows', 'system32', 'syswow64']):
                        continue
                    
                    for name in files:
                        # 跳过系统文件类型
                        if os.path.splitext(name)[1].lower() in skip_extensions:
                            continue
                            
                        file_path = os.path.join(root, name)
                        self.files_processed += 1
                        
                        # 只处理超过1天的文件
                        try:
                            if time.time() - os.path.getmtime(file_path) < 86400:  # 24小时
                                continue
                        except:
                            continue
                        
                        # 尝试删除文件
                        if self.try_delete_file(file_path):
                            files_count += 1
                        
                        # 更新进度（减少更新频率）
                        if files_count % 20 == 0:
                            current_progress = min(90, int((files_count / 500) * 100))
                            self.gui.update_progress(current_progress)
                    
                    # 尝试删除空文件夹
                    try:
                        if not os.listdir(root):
                            os.rmdir(root)
                    except:
                        pass
                    
            except Exception as e:
                logging.error(f"处理文件夹 {folder} 时出错: {str(e)}")
                continue
        
        self.gui.update_progress(100)
        self.gui.add_completed_task("系统存储清理", 
                                  f"释放空间: {self.get_size_format(self.task_cleaned)}")
        self.total_cleaned += self.task_cleaned  # 累加到总清理空间
        self.gui.next_task()

    def clean_system(self):
        """执行系统清理"""
        try:
            self.gui.update_status("开始清理", "正在初始化...")
            
            # 1. 清理临时文件
            self.clean_temp_folders()
            
            # 2. 关闭系统休眠
            self.disable_hibernation()
            
            # 3. 清理系统存储
            self.clean_system_storage()
            
            # 4. 显示完成信息
            if self.gui.current_task >= self.gui.total_tasks:
                self.gui.show_completion(self.get_size_format(self.total_cleaned))
                
        except Exception as e:
            logging.error(f"清理过程中发生错误: {str(e)}")
            self.gui.update_status("清理出错", str(e))

def main():
    # 确保以管理员权限运行
    if not run_as_admin():
        input("无法获取管理员权限，按Enter键退出...")
        sys.exit(1)
        
    setup_logging()
    logging.info("程序已以管理员权限启动")
    
    # 创建并启动GUI
    app = CleanerGUI()
    app.start_cleaning()
    app.root.mainloop()

if __name__ == "__main__":
    main()
