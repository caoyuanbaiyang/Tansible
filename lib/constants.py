import datetime
import logging
import os
import re
import sys
from fnmatch import fnmatchcase as match

import chardet

from lib.logger import logger
from lib.readcfg import ReadCfg


DEFAULT_CONFIG_DIR = "config/"
DEFAULT_LOG_DIR = "logs/"

DEFAULT_HOSTS_FILE = DEFAULT_CONFIG_DIR + "hosts.yaml"
DEFAULT_GROUPS_FILE = DEFAULT_CONFIG_DIR + "groups.yaml"
DEFAULT_ACTION_FILE = DEFAULT_CONFIG_DIR + "action.yaml"

SYSTEM_NOTE_REGULAR_MATCH = r'.*~]\$ |.*~> |.*]\$ |.*\$ '

DEFAULT_CONNECT_TIMEOUT = 3
DEFAULT_COMMAND_EXEC_TIMEOUT = 60
DEFAULT_SSH_END_PATTERN = r'[\$#>] $'

current_time = datetime.datetime.now()
formatted_time = current_time.strftime('%Y%m%d-%H%M%S')
log_file = DEFAULT_LOG_DIR + "tansible"+formatted_time+".log"

if not os.path.exists("logs"):
    os.mkdir("logs")

log = logger(log_file, clevel=logging.INFO, Flevel=logging.DEBUG)


def system_match(line):
    """
    使用正则检查该行是否匹配
    :param line:
    :return:
    """
    return re.match(SYSTEM_NOTE_REGULAR_MATCH, line)

def decode_line(line):
    try:
        line = line.decode('UTF-8')
    except:
        try:
            line = line.decode('GBK')
        except:
            log.error(f'decode utf-8/GBK error #{line}#')
            return ''
    return line

def load_actions_file(actions_file):
    actions_cfg_file = actions_file if actions_file is not None else DEFAULT_ACTION_FILE
    if os.path.exists(actions_cfg_file):
        return ReadCfg().readcfg(actions_cfg_file), actions_cfg_file
    else:
        raise Exception(f"actions配置文件{actions_cfg_file}不存在")


def adjust_window_size():
    choice = input("是否运行，借机调整窗口大小吧（y/n）：")
    if choice not in ["y", "n"]:
        print("输入错误")
        raise Exception("输入错误")
    if choice == "n":
        print("选择退出...")
        raise Exception("选择退出...")


def step_by_step_choice():
    """单步运行模式，选择y 则继续单步运行，选择q则退出程序，选择go，则退出单步运行模式，后续为正常运行"""
    choice = input("单步运行模式，此处暂停，如需继续请按y，退出程序请按q，退出单步运行模式请按go：")
    single_step = True
    if choice not in ["y", "q", "go"]:
        print("输入错误")
        raise Exception("输入错误")
    if choice == "q":
        print("选择退出...")
        sys.exit(0)
    if choice == "go":
        print("选择退出单步运行模式...")
        single_step = False
    return single_step


def breakpoint_choice(point_name):
    """单步运行模式下的断点设置，选择y 则继续运行，选择q则退出程序"""
    choice = input(f"断点{point_name}，此处暂停，如需继续请按y，退出请按q：")
    if choice not in ["y", "q"]:
        print("输入错误")
        raise Exception("输入错误")
    if choice == "q":
        print("选择退出...")
        sys.exit(0)


def PackHost(pub_cfg, host_cfg):
    # 判断连接配置采用何种配置，采用public部分还是采用host部分
    # 采用password 方式还是 采用 pkey方式
    for pub_key in pub_cfg.keys():
        if pub_key not in host_cfg.keys():
            host_cfg[pub_key] = pub_cfg.get(pub_key)

    if "username" not in host_cfg.keys() and "username" not in pub_cfg.keys():
        raise Exception("配置错误，用户名未配置")

    if "password" not in pub_cfg.keys() and "password" not in host_cfg.keys() and "key_filename" not in host_cfg.keys() and "key_filename" not in pub_cfg.keys():
        raise Exception("配置错误，连接方式未配置")


# 为兼容旧版，创建一个模块翻译的字典
MODULE_TRANS_DICT = {
    "shell": "Tshell",
    "sftp": "Tsftp",
    "upload": "Tupload",
    "vsget1": "Tvsget1",
    "passwd": "SysPwdModify",
}


def exclude_files(filename, dir_filename, excludes=[]):  # 是否属于不下载的文件判断
    # exclude 为具体配置，支持文件名配置及带目录的配置   # exclude 的不下载，跳过本次循环，进入下一循环
    if filename in excludes or dir_filename in excludes:
        return True

    # exclude 为模糊配置，配置的话就不下载，跳过本次循环，进入下一循环
    for exclude in excludes:
        if match(filename, exclude) or match(dir_filename, exclude):
            return True

    # 以上情况都不是这返回False
    return False


def isContrainSpecialCharacter(string):
    # fnmatch 支持的模糊匹配通配符
    special_character = r"*?[]!"
    for i in special_character:
        if i in string:
            return True
    return False


def decode_byte_string(byte_string):
    # 检测字节对象的编码类型
    detected_encoding = chardet.detect(byte_string)['encoding']

    # 根据检测到的编码类型进行解码
    decoded_string = byte_string.decode(detected_encoding)

    return decoded_string