# -*- coding: utf-8 -*-
import os

import chardet

from lib.tools import Tools
import paramiko
import time
import json
from lib.readcfg import ReadCfg


def ssh_reply(chanel_recv):
    buff = ""
    whcode = chardet.detect(chanel_recv)['encoding']
    if whcode == "ISO-8859-2":
        reply = chanel_recv.decode('gbk', 'ignore')
    elif whcode == "utf-8":
        reply = chanel_recv.decode('utf8', 'ignore')
    else:
        reply = chanel_recv.decode('ascii', 'ignore')
    buff += reply
    return buff


class ModelClass(object):
    def __init__(self, mylog):
        self.mylog = mylog

    def shellCommand(self, ssh, command, stdinfo, timeout=5):
        chanel = ssh.invoke_shell()
        time.sleep(0.1)
        chanel.send(command + "\n")

        buff = ""
        while not (buff.endswith("assword: ") or buff.endswith("密码：")):
            resp = chanel.recv(9999)
            reply = ssh_reply(resp)
            buff += reply

        for info in stdinfo:
            chanel.send(info)
            chanel.send("\n")
            time.sleep(0.1)

        buff = ""
        while not buff.endswith("$ "):
            resp = chanel.recv(9999)
            reply = ssh_reply(resp)
            buff += reply

        self.mylog.info(buff)
        return [True, buff]

    def modifyNewPassword(self, hostname, ssh, password, newpassword):
        stdinfo = [password, newpassword, newpassword]
        rs = self.shellCommand(ssh, "passwd", stdinfo)

        if type(rs[1]) == str:
            if "successfully" in rs[1] or "成功" in rs[1]:
                self.mylog.info("修改密码：主机{}修改成功".format(hostname))
            else:
                self.mylog.error("修改密码：主机{}修改失败".format(hostname))

    def checkwd(self, hostname, ssh, username, password):
        rs = self.shellCommand(ssh, "su - {}".format(username), [password])

        if type(rs[1]) == str:
            if "Last login" in rs[1] or "上一次登录" in rs[1]:
                self.mylog.info("检查：主机{}登录检查成功".format(hostname))
            else:
                self.mylog.error("检查：主机{}登录检查失败".format(hostname))

    def action(self, ssh, hostname, param, hostparam=None):
        if hostparam is None:
            hostparam = []
        current_pwd = ""
        new_pwd = ""
        if "current_pwd" in param:
            current_pwd = param["current_pwd"]
        if "current_pwd_file" in param:
            current_pwd = ReadCfg().readcfg(os.path.join("config", param["current_pwd_file"]))[hostname]
        if "new_pwd" in param:
            new_pwd = param["new_pwd"]
        if "new_pwd_file" in param:
            new_pwd = ReadCfg().readcfg(os.path.join("config", param["new_pwd_file"]))[hostname]

        if param["action"] == "modify":
            self.modifyNewPassword(hostname, ssh, current_pwd, new_pwd)
        elif param["action"] == "checknew":
            self.checkwd(hostname, ssh, hostparam["username"], new_pwd)
        elif param["action"] == "checkcur":
            self.checkwd(hostname, ssh, hostparam["username"], current_pwd)
        else:
            raise Exception('配置文件配置错误:未知action参数' + json.dumps(param))


if __name__ == '__main__':
    pass
