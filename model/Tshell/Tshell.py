# -*- coding: utf-8 -*-

import json
import os
import time

import chardet
import paramiko


def ssh_reply(chanel_recv):
    whcode = chardet.detect(chanel_recv)['encoding']
    reply = chanel_recv.decode(whcode, 'ignore')
    return reply


class ModelClass(object):
    def __init__(self, mylog):
        self.mylog = mylog

    def execcommand(self, ssh, command, timeout=5):
        try:
            chanel = ssh.invoke_shell()
            chanel.send("export LANG=en_US.UTF-8 \n")
            time.sleep(0.01)
            chanel.send(command + "\n")
            time.sleep(0.01)

            buff = ""
            i = 0
            while not buff.endswith("$ "):
                resp = chanel.recv(9999)
                time.sleep(0.01)
                reply = ssh_reply(resp)
                buff = reply
                i = i + 1
                while i > 50:
                    break

        except paramiko.ssh_exception.SSHException:
            self.mylog.info("命令执行失败:" + command)
            return [False, "命令执行失败:" + command]
        except Exception as e:
            self.mylog.info(e)
            self.mylog.info("命令执行失败:" + command)
            return [False, e]

        self.mylog.info(buff)
        return [True, buff]

    def action(self, ssh, hostname, param, hostparam=None):
        if hostparam is None:
            hostparam = []
        for cfg_key, cfg_value in param.items():
            if cfg_key not in ["cmd"]:
                raise Exception('配置文件配置错误:未知参数:{param}'.format(param=json.dumps(param)))
        self.execcommand(ssh, param["cmd"])
