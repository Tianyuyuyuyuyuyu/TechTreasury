import sys
import traceback
import logging
from PyQt5.QtWidgets import QApplication
from gui import PDFConverterGUI

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def handle_exception(exc_type, exc_value, exc_traceback):
    """处理未捕获的异常"""
    logger = logging.getLogger(__name__)
    logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

def main():
    try:
        logger = setup_logging()
        # 设置异常处理器
        sys.excepthook = handle_exception
        
        # 创建应用实例
        app = QApplication(sys.argv)
        
        # 创建主窗口
        window = PDFConverterGUI()
        window.show()
        
        # 启动应用
        sys.exit(app.exec_())
    except Exception as e:
        logger.error(f"程序启动失败: {str(e)}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 