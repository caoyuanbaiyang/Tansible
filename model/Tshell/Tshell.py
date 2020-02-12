# -*- coding: utf-8 -*-

import json
import os
import paramiko


class ModelClass(object):
    def __init__(self, mylog):
        self.mylog = mylog

    def execcommand(self, ssh, command, stdinfo=[], timeout=5):
        try:
            stdin, stdout, stderr = ssh.exec_command("echo $LANG")
            langset = stdout.readlines()[0].replace("\n", "").split(".")[1]
        except paramiko.ssh_exception.SSHException:
            self.mylog.info("LANG获取失败")
            raise Exception("LANG获取失败")
        try:
            stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
            self.mylog.info(command)
            for info in stdinfo:
                stdin.write(info+"\n")
                self.mylog.info(info)
            if stderr.readable():
                err = stderr.read()
                err = err.decode(langset)
            if stdout.readable():
                out = stdout.read()
                out = out.decode(langset)
            self.mylog.info("命令out:\n"+"".join(out))
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
        for cfg_key, cfg_value in param.items():
            if cfg_key not in ["cmd"]:
                raise Exception('配置文件配置错误:未知参数:{param}'.format(param=json.dumps(param)))
        self.execcommand(ssh, param["cmd"])
