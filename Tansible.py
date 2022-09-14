# -*- coding: utf-8 -*-

import datetime
import traceback

from lib.readcfg import ReadCfg
from lib.Logger import logger
import logging
import importlib
from lib.tools import Tools
import paramiko
import os
from concurrent.futures import ThreadPoolExecutor
from lib.hosts import hosts

now_time = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
log_file = "syslog.log"
hosts_file = "config/hosts.yaml"
groups_file = "config/groups.yaml"
action_file = "config/action.yaml"


class Tansible(object):
    def __init__(self, filepath=None):
        self.mylog = logger(log_file, logging.INFO, logging.DEBUG)
        self.hosts = ReadCfg().readcfg(hosts_file)
        if os.path.exists(groups_file):
            self.groups = ReadCfg().readcfg(groups_file)
        else:
            self.groups = []

        if filepath is None:
            self.action_cfg = ReadCfg().readcfg(action_file)
            self.cfgfilepath = action_file
        else:
            self.action_cfg = ReadCfg().readcfg(filepath)
            self.cfgfilepath = filepath

        if "max_workers" in self.action_cfg["PUBLIC"]:
            self.max_workers = self.action_cfg["PUBLIC"]["max_workers"]
        else:
            self.max_workers = 1

    def __check_acton_hostcfg(self, hostobj):
        hostnames = []
        err_rt_hostnames = []
        for action in self.action_cfg["ACTION"]:
            ok_hostnames, err_hostnames = hostobj.get_host_name(action["hosts"])
            hostnames = hostnames + ok_hostnames
            err_rt_hostnames = err_rt_hostnames + err_hostnames
        if len(err_rt_hostnames) != 0:
            return False, err_rt_hostnames
        else:
            return True, []

    def __action_func_inner(self, hostname, modelname, param):
        self.mylog.info("------模块:{mod},主机:{host}".format(host=hostname, mod=modelname))
        host = self.hosts["HOST"][hostname]

        Tools().packHost(self.hosts["PUBLIC"], host)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        if host["connect_type"] == 1:
            # 用户名密码 登录
            connect = Tools().connectWithPWD(ssh, host["ip"], host["username"], host["password"])
        else:
            # rsa 密码文件登录
            pkey = paramiko.RSAKey.from_private_key_file(password=host["passphrase"],
                                                         filename=host["key_filename"])
            connect = Tools().connectWithRSA(ssh, host["ip"], host["username"], pkey)
        if connect:
            if modelname == "CheckConnect":
                self.mylog.info("连接成功")
            else:
                m = importlib.import_module("model." + modelname + "." + modelname)
                m.ModelClass(self.mylog).action(ssh, hostname, param, host)
            ssh.close()
        else:
            self.mylog.cri(f"连接失败， 主机名：{hostname} IP：{host['ip']} 用户名：{host['username']}")

    def action_func(self):
        # 检查hosts 配置是否有错误的，如果有错误，则不运行
        hostobj = hosts(self.mylog, self.groups, self.hosts)
        checkrz, rzlist = self.__check_acton_hostcfg(hostobj)
        if not checkrz:
            self.mylog.cri(f"action 配置文件中hosts配置错误，hosts.yaml无相关配置：{rzlist}")
            raise Exception("action 配置文件hosts配置错误")

        self.mylog.green(f'############开始任务{self.cfgfilepath}############')
        choise = input("是否运行，借机调整窗口大小吧（y/n）：")
        if choise not in ["y", "n"]:
            print("输入错误")
            raise Exception("输入错误")
        if choise == "n":
            print("选择退出...")
            raise Exception("选择退出...")
        ignore_list = []
        for action in self.action_cfg["ACTION"]:
            # 遍历hosts列表
            hostname_list, err_host_list = hostobj.get_host_name(action["hosts"])
            for task in action["tasks"]:
                # 遍历task列表
                taskname = None
                if "name" in task:
                    taskname = task["name"]
                    self.mylog.info('*********执行任务：{task}*********'.format(task=task["name"]))
                # 模块信息
                for modelname, param in task.items():
                    if modelname == "name":
                        continue
                    if modelname == "GetHostList":
                        self.mylog.info(f"主机列表：{hostname_list}")
                        continue
                    with ThreadPoolExecutor(max_workers=self.max_workers) as t:
                        obj_list = []
                        for hostname in hostname_list:
                            try:
                                obj = t.submit(self.__action_func_inner, hostname, modelname, param)
                                obj_list.append(obj)
                            except Exception as e:
                                ignore_list = ignore_list + (self.__except_deal(hostname, modelname, param, taskname))
        if ignore_list:
            self.mylog.cri(f"忽略的任务：{ignore_list}")
        self.mylog.green('############所有任务完成############')

    def __except_deal(self, hostname, modelname, param, taskname=None):
        ignore_list = []
        self.mylog.cri(f"traceback.format_exc():{traceback.format_exc()}")
        if "exception_deal" in self.action_cfg["PUBLIC"]:
            if self.action_cfg["PUBLIC"]["exception_deal"] not in ["c", "e", "r", "q"]:
                raise Exception("公共参数exception_deal配置错误")
            exception_deal = self.action_cfg["PUBLIC"]["exception_deal"]
        else:
            exception_deal = "q"
        if exception_deal == "q":
            print("请选择异常处理：")
            print(f"c: 忽略该错误，继续执行")
            print("e: 终止程序，程序将退出")
            print(f"r: 重试")
            exception_deal = input("请输入操作代码[c/e/r]：")
        if exception_deal == "c":
            self.mylog.info("选择c,忽略该错误，继续执行")
            ignore_list.append({"host": hostname, "model": modelname, "task": taskname})
        if exception_deal == "e":
            self.mylog.info("选择e,终止程序")
            raise
        if exception_deal == "r":
            self.mylog.info("选择r,重新执行任务")
            self.__action_func_inner(hostname, modelname, param)
        return ignore_list
