# -*- coding: utf-8 -*-
import os

from lib.tools import Tools
import paramiko
import time
import json
from lib.readcfg import ReadCfg


class ModelClass(object):
    def __init__(self, mylog):
        self.mylog = mylog

    def shellCommand(self, ssh, command, stdinfo, timeout=5):
        try:
            stdin, stdout, stderr = ssh.exec_command("echo $LANG")
            langset = stdout.readlines()[0].replace("\n", "").split(".")[1]
        except paramiko.ssh_exception.SSHException:
            self.mylog.info("LANG获取失败")
            raise Exception("LANG获取失败")
        try:
            stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout, get_pty=True)
            self.mylog.info("执行命令:{}".format(command))
            time.sleep(0.5)

            for info in stdinfo:
                stdin.write("{}\n".format(info))
                time.sleep(0.5)
                self.mylog.info("输入:{}".format(info))
            stdin.flush()

            timeout = 2.2
            endtime = time.time() + timeout

            if stderr.readable():
                while not stderr.channel.eof_received:
                    time.sleep(0.5)
                    if time.time() > endtime:
                        stderr.channel.close()
                        break
                err = stderr.read()
                err = err.decode(langset)

            endtime = time.time() + timeout

            if stdout.readable():
                while not stdout.channel.eof_received:
                    time.sleep(0.5)
                    if time.time() > endtime:
                        stdout.channel.close()
                        break
                out = stdout.read()
                out = out.decode(langset)
            self.mylog.info("命令out:" + "".join(out))
            self.mylog.info("命令err:" + "".join(err))
        except paramiko.ssh_exception.SSHException:
            self.mylog.error("命令执行失败:" + command)
            return [False, "命令执行失败:" + command]
        except Exception as e:
            self.mylog.info(e)
            self.mylog.error("命令执行失败:" + command)
            return [False, e]

        return [True, out]

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
        if "current_pwd" in param and "new_pwd" in param:
            current_pwd = param["current_pwd"]
            new_pwd = param["new_pwd"]
        if "current_pwd_file" in param and "new_pwd_file" in param:
            current_pwd = ReadCfg().readcfg(os.path.join("config", param["current_pwd_file"]))[hostname]
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
