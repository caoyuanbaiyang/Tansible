# -*- coding: utf-8 -*-
from lib.tools import Tools
import paramiko
import json


class ModelClass(object):
    def __init__(self, mylog):
        self.mylog = mylog

    def checkhostname(self, ssh, hostname, stdinfo, timeout=3):
        result = self.execcommand(ssh, "hostname", stdinfo, timeout=timeout)
        cmdhostname = result[1].split("\n")[-2].strip()
        if cmdhostname == hostname:
            return True, cmdhostname
        else:
            return False, cmdhostname

    def execcommand(self, ssh, command, stdinfo=[], timeout=5):
        try:
            stdin, stdout, stderr = ssh.exec_command("echo $LANG")
            langset = stdout.readlines()[0].replace("\n", "").split(".")[1]
        except paramiko.ssh_exception.SSHException:
            self.mylog.info("LANG获取失败")
            raise Exception("LANG获取失败")
        try:
            stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
            # self.mylog.info(command)
            for info in stdinfo:
                stdin.write(info+"\n")
                self.mylog.info(info)
            if stderr.readable():
                err = stderr.read()
                err = err.decode(langset)
            if stdout.readable():
                out = stdout.read()
                out = out.decode(langset)
            # self.mylog.info("命令out:"+"".join(out))
        except paramiko.ssh_exception.SSHException:
            self.mylog.info("命令执行失败:"+command)
            return [False, "命令执行失败:"+command]
        except Exception as e:
            self.mylog.info(e)
            self.mylog.info("命令执行失败:"+command)
            return [False, e]
        if len(err) != 0:
            self.mylog.info("命令err:" + "".join(err))
            return [False, "".join(err)]
        return [True, out]

    def action(self, ssh, hostname, param):
        stdinfo = []
        rz, cmdhostname = self.checkhostname(ssh, hostname, stdinfo)
        if rz:
            self.mylog.info("主机名检查--成功")
        else:
            self.mylog.error(f"主机名检查--失败 cfg:{hostname} result:{cmdhostname}")
