# -*- coding: utf-8 -*-

import json
import os
import re
import time

import chardet
import paramiko


class ModelClass(object):
    def __init__(self, mylog):
        self.mylog = mylog

    def __execcommand(self, ssh, command, v_lst_instr=None, v_lst_input=None, timeout=5):
        try:
            channel = ssh.invoke_shell()
            channel.send("export LANG=en_US.UTF-8 \n")
            time.sleep(0.01)
            channel.send(command + "\n")

            rst = ""
            while not rst.endswith("$ "):
                time.sleep(0.1)
                rst = channel.recv(1024)
                rst = rst.decode('utf-8', 'ignore')
                for line in rst.splitlines():
                    if line != "":
                        self.mylog.info('out: ' + line)
                # 通过命令执行提示符来判断命令是否执行完成
                for c, instr in enumerate(v_lst_instr, 0):
                    if instr in rst:
                        channel.send(v_lst_input[c] + '\r')
                        if c == len(v_lst_input) - 1:
                            time.sleep(0.1)
                            rst = channel.recv(1024)
                            rst = rst.decode('utf-8', 'ignore')
                            for line in rst.splitlines():
                                if line != "":
                                    self.mylog.info('out: ' + line)
                            break

        except paramiko.ssh_exception.SSHException:
            self.mylog.info("命令执行失败:" + command)
            return False
        except Exception as e:
            self.mylog.info(e)
            self.mylog.info("命令执行失败:" + command)
            return False

        return True

    def action(self, ssh, hostname, param, hostparam=None):
        if hostparam is None:
            hostparam = []
        for cfg_key, cfg_value in param.items():
            if cfg_key not in ["cmd", "input", "instr"]:
                raise Exception('配置文件配置错误:未知参数:{param}'.format(param=json.dumps(param)))
        if not ("instr" in param) or param["instr"] is None:
            v_lst_instr = []
        else:
            v_lst_instr = param["instr"]
        if not ("input" in param) or param["input"] is None:
            v_lst_input = []
        else:
            v_lst_input = param["input"]

        self.__execcommand(ssh, param["cmd"], v_lst_instr, v_lst_input)
