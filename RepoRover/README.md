# RepoRover - GitHub文件下载工具

RepoRover 是一个用于从 GitHub 仓库下载指定后缀文件的 Windows GUI 工具。它允许用户无需克隆整个仓库，即可下载特定类型的文件。

## 功能特点

- 支持从公开/私有 GitHub 仓库下载文件
- 支持指定多个文件后缀
- 递归处理子目录
- 用户友好的图形界面
- 实时下载进度显示
- 详细的日志记录

## 安装要求

- Windows 操作系统
- 无需 Python 环境（已打包为独立可执行文件）

## 使用方法

1. 运行程序
2. 输入 GitHub 仓库 URL
3. 指定要下载的文件后缀（如 .py, .js, .md）
4. 选择保存文件的目标文件夹
5. 点击"开始下载"按钮

## 开发环境设置

```bash
# 克隆仓库
git clone [repository-url]

# 安装依赖
pip install -r requirements.txt

# 运行程序
python main.py
``` 