# -*- coding: utf-8 -*-
import os
import json
from lib.readcfg import ReadCfg


class ModelClass(object):
    def __init__(self, mylog):
        self.mylog = mylog

    def modifyNewPassword(self, hostname, ssh, password, newpassword):
        cmd = f"echo -e '{password}\n{newpassword}\n{newpassword}\n' | passwd"
        stdin, stdout, stderr = ssh.exec_command(cmd)

        # 读取命令执行结果
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')

        if stderr.read().decode():
            self.mylog.error(f"修改密码：修改失败-{error}")
        else:
            self.mylog.info(f"修改密码：修改成功-{output}")

    def checkwd(self, hostname, ssh, username, password):
        cmd = f"echo '{password}' | su - {username}"
        stdin, stdout, stderr = ssh.exec_command(cmd)

        # 读取命令执行结果
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')

        # 输出命令执行结果
        if error:
            self.mylog.error(f"检查：主机登录检查失败-{error}")
        else:
            self.mylog.info(f"检查：主机登录检查成功-{output}")

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
