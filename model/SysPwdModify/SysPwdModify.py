# -*- coding: utf-8 -*-
import os

import chardet

# from lib.tools import Tools
# import paramiko
import time
import json
from lib.readcfg import ReadCfg


def ssh_reply(chanel_recv):
    whcode = chardet.detect(chanel_recv)['encoding']
    reply = chanel_recv.decode(whcode, 'ignore')
    return reply


class ModelClass(object):
    def __init__(self, mylog):
        self.mylog = mylog

    def shellCommand(self, ssh, command, stdinfo, timeout=10):
        channel = ssh.invoke_shell()
        channel.send("export LANG=en_US.UTF-8 \n")
        time.sleep(0.01)
        channel.send(command + "\n")
        time.sleep(0.05)

        return_bool = True
        buff = ""
        i = 0
        self.mylog.debug("开始查找assword:")
        while not (buff.endswith("assword: ") or buff.endswith("密码：")):
            self.mylog.debug("查找assword:...")
            time.sleep(0.1)
            resp = channel.recv(9999)
            reply = ssh_reply(resp)
            buff += reply
            i = i + 1
            while i > 50:
                break

        self.mylog.debug("输入信息")
        for info in stdinfo:
            while not channel.send_ready():
                time.sleep(0.009)
            channel.send(info)
            channel.send("\n")
            self.mylog.debug(f"输入:{info}")
            time.sleep(0.2)

        buff = ""

        self.mylog.debug("开始查找$ ")
        base_time = time.time()
        while not buff.endswith("$ "):
            while not channel.recv_ready():
                self.mylog.debug("sleep 0.9")
                time.sleep(0.9)
                if time.time() >= (base_time + timeout):
                    return [True, f"channel.recv_ready time out, buff:{buff}"]
            self.mylog.debug("channel.recv(9999)")
            resp = channel.recv(9999)
            reply = ssh_reply(resp)
            buff += reply
            self.mylog.debug(f"reply:{reply}")
            if "BAD PASSWORD" in buff:
                return_bool = False
                break

        self.mylog.debug(f"buff:{buff}")
        return [return_bool, buff]

    def modifyNewPassword(self, hostname, ssh, password, newpassword):
        stdinfo = [password, newpassword, newpassword]
        rs = self.shellCommand(ssh, "passwd", stdinfo)

        if type(rs[1]) == str:
            self.mylog.debug(f"rs1内容：{rs[1]}")
            if "successfully" in rs[1] or "成功" in rs[1]:
                self.mylog.info("修改密码：主机{}修改成功".format(hostname))
            elif "manipulation error" in rs[1]:
                self.mylog.error("修改密码：主机{}修改失败,当前密码错误".format(hostname))
                raise Exception("修改密码：主机{}修改失败,当前密码错误".format(hostname))
            elif "BAD PASSWORD" in rs[1]:
                self.mylog.error("修改密码：主机{}修改失败,新密码不符合要求".format(hostname))
                raise Exception("修改密码：主机{}修改失败,新密码不符合要求".format(hostname))
            else:
                self.mylog.error("修改密码：主机{}修改失败".format(hostname))
                raise Exception("修改密码：主机{}修改失败".format(hostname))

    def checkwd(self, hostname, ssh, username, password):
        rs = self.shellCommand(ssh, f"su - {username}", [password])

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
