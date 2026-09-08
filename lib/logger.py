# coding=utf-8
import logging
import sys
import platform

# ==================== 跨平台颜色配置 ====================
# Windows 颜色常量（保留原有）
FOREGROUND_WHITE = 0x0007
FOREGROUND_BLUE = 0x01
FOREGROUND_GREEN = 0x02
FOREGROUND_RED = 0x04
FOREGROUND_YELLOW = FOREGROUND_RED | FOREGROUND_GREEN

# Linux/macOS ANSI 颜色转义码
ANSI_COLORS = {
    FOREGROUND_GREEN: '\033[32m',    # 绿色
    FOREGROUND_YELLOW: '\033[33m',   # 黄色
    FOREGROUND_RED: '\033[31m',      # 红色
    FOREGROUND_WHITE: '\033[0m'      # 重置（白色/默认）
}

# 检测系统类型
SYSTEM = platform.system().lower()
IS_WINDOWS = SYSTEM == 'windows'
IS_LINUX = SYSTEM == 'linux'

# Windows 专属：加载 kernel32（仅Windows生效）
if IS_WINDOWS:
    import ctypes
    STD_OUTPUT_HANDLE = -11
    std_out_handle = ctypes.windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)


# ==================== 跨平台颜色设置函数 ====================
def set_color(color):
    """
    跨平台设置控制台文本颜色
    :param color: 颜色常量（兼容Windows/Linux）
    """
    try:
        # 非交互式终端（如后台运行），不设置颜色
        if not sys.stdout.isatty():
            return

        if IS_WINDOWS:
            # Windows：使用ctypes设置颜色
            ctypes.windll.kernel32.SetConsoleTextAttribute(std_out_handle, color)
        elif IS_LINUX:
            # Linux：输出ANSI转义码
            ansi_code = ANSI_COLORS.get(color, ANSI_COLORS[FOREGROUND_WHITE])
            sys.stdout.write(ansi_code)
            sys.stdout.flush()
    except Exception:
        # 兼容无控制台/权限不足场景，静默失败
        pass


# ==================== 日志类 ====================
class logger:  # 类名规范：首字母大写（原logger改为Logger）
    def __init__(self, path, clevel=logging.DEBUG, Flevel=logging.DEBUG):
        self.logger = logging.getLogger(path)
        self.logger.setLevel(logging.DEBUG)
        # 避免重复添加处理器（多次实例化时的坑）
        if self.logger.handlers:
            self.logger.handlers.clear()

        # 控制台日志格式
        sh_fmt = logging.Formatter('[%(asctime)s] - [%(levelname)s] - %(message)s')
        sh_fmt.datefmt = '%H:%M:%S'
        sh = logging.StreamHandler()
        sh.setFormatter(sh_fmt)
        sh.setLevel(clevel)

        # 文件日志格式
        fh_fmt = logging.Formatter('[%(asctime)s] - [%(threadName)s] - [%(levelname)s] - %(message)s')
        fh = logging.FileHandler(path, encoding='utf-8')
        fh.setFormatter(fh_fmt)
        fh.setLevel(Flevel)

        self.logger.addHandler(sh)
        self.logger.addHandler(fh)

    def green(self, message, color=FOREGROUND_GREEN):
        set_color(color)
        self.logger.info(message)
        set_color(FOREGROUND_WHITE)

    def debug(self, message):
        self.logger.debug(message)

    def info(self, message):
        self.logger.info(message)

    def war(self, message, color=FOREGROUND_YELLOW):
        set_color(color)
        self.logger.warning(message)
        set_color(FOREGROUND_WHITE)

    def error(self, message, color=FOREGROUND_RED):
        set_color(color)
        self.logger.error(message)
        set_color(FOREGROUND_WHITE)

    def cri(self, message, color=FOREGROUND_RED):
        set_color(color)
        self.logger.critical(message)
        set_color(FOREGROUND_WHITE)


# ==================== 测试代码 ====================
if __name__ == '__main__':
    log = logger('yyx.log', logging.INFO, logging.INFO)
    log.debug('一个debug信息')
    log.info('一个info信息')
    log.green('一个绿色的info信息')
    log.war('一个warning信息')
    log.error('一个error信息')
    log.cri('一个致命critical信息')
