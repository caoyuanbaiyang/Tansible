# -*- coding: utf-8 -*-

import datetime
from lib.readcfg import ReadCfg
from lib.Logger import logger
import logging
import importlib
from lib.tools import Tools
import paramiko
import os


now_time = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
log_file = "syslog.log"
hosts_file = "config/hosts.yaml"
groups_file = "config/groups.yaml"
action_file = "config/action.yaml"


class Tansible(object):
    def __init__(self, filepath=None):
        self.mylog = logger(log_file, logging.INFO, logging.INFO)
        self.hosts = ReadCfg().readcfg(hosts_file)
        if os.path.exists(groups_file):
            self.groups = ReadCfg().readcfg(groups_file)
        else:
            self.groups = []
        if filepath is None:
            self.action_cfg = ReadCfg().readcfg(action_file)
        else:
            self.action_cfg = ReadCfg().readcfg(filepath)

    def __get_host_name(self, hostsnames):
        # hostsnames 可以是列表，可以是ALL，可以是具体主机名
        # 还可以是组名
        rt_hostnames = []
        if isinstance(hostsnames, list):
            # hosts.yaml 中部分主机 或 groups.yaml中指定的组
            for host in hostsnames:
                if host in self.groups:
                    # host 是组，需要获取组员
                    if isinstance(self.groups[host], dict):
                        # 嵌套组
                        if "children" not in self.groups[host]:
                            self.mylog.cri("嵌套组配置错误，必须有children关键字")
                            raise Exception("嵌套组配置错误，必须有children关键字")
                        for children_group in self.groups[host]["children"]:
                            rt_hostnames = rt_hostnames + self.groups[children_group]
                    else:
                        # 非嵌套组
                        rt_hostnames = rt_hostnames + self.groups[host]
                else:
                    # host 是具体的主机
                    rt_hostnames.append(host)

        elif isinstance(hostsnames, str):
            if hostsnames == "ALL":
                # hosts.yaml 中全部的主机
                for hostname in self.hosts["HOST"]:
                    rt_hostnames.append(hostname)
            else:
                # hosts.yaml 中某一台主机，后续弃用，先保持兼容
                rt_hostnames.append(hostsnames)
        else:
            raise Exception("action文件hosts配置有误")
        return rt_hostnames

    def __check_hostname(self, hostsnames):
        # hostnames 为主机名列表，该函数检查主机名是否在hosts.yaml中
        rt_hostnames = []
        for hostname in hostsnames:
            if hostname not in self.hosts["HOST"]:
                # 检查失败，不在hosts.yaml中
                rt_hostnames.append(hostname)
        return rt_hostnames

    def __check_acton_hostcfg(self):
        hostnames = []
        err_hostnames = []
        for action in self.action_cfg["ACTION"]:
            hostnames = hostnames + self.__get_host_name(action["hosts"])
            err_hostnames = err_hostnames + self.__check_hostname(hostnames)
        if len(err_hostnames) != 0:
            return False, err_hostnames
        else:
            return True, []

    def __action_func_inner(self, hostname, modelname, param):
        self.mylog.info("------模块:{mod},主机:{host}" .format(host=hostname, mod=modelname))
        host = self.hosts["HOST"][hostname]

        Tools().packHost(self.hosts["PUBLIC"], host)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        if host["connet_type"] == 1:
            # 用户名密码 登录
            connect = Tools().connectWithPWD(ssh, host["ip"], host["username"], host["password"])
        else:
            # rsa 密码文件登录
            pkey = paramiko.RSAKey.from_private_key_file(password=host["passphrase"],
                                                         filename=host["key_filename"])
            connect = Tools().connectWithRSA(ssh, host["ip"], host["username"], pkey)
        if connect:
            m = importlib.import_module("model." + modelname + "." + modelname)
            m.ModelClass(self.mylog).action(ssh, hostname, param)
            ssh.close()
        else:
            self.mylog.cri("连接失败")

    def action_func(self):
        # 检查hosts 配置是否有错误的，如果有错误，则不运行
        checkrz, rzlist = self.__check_acton_hostcfg()
        if not checkrz:
            self.mylog.cri(f"action 配置文件中hosts错误：{rzlist}")
            raise Exception("action 位置文件hosts配置错误")

        for action in self.action_cfg["ACTION"]:
            # 遍历hosts列表
            hostname_list = self.__get_host_name(action["hosts"])
            for task in action["tasks"]:
                # 遍历task列表
                self.mylog.info('#########执行任务：{task}#########'.format(task=task["name"]))
                # 模块信息
                for modelname, param in task.items():
                    if modelname == "name":
                        continue
                    for hostname in hostname_list:
                        self.__action_func_inner(hostname, modelname, param)
        self.mylog.info('#########所有任务完成#########')