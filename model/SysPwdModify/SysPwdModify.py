# -*- coding: utf-8 -*-
import json
import os

from lib.readcfg import ReadCfg


class ModelClass(object):
    def __init__(self, mylog, conn, hostname, action_param, host_param):
        self.mylog = mylog
        self.conn = conn
        self.hostname = hostname
        self.action_param = action_param
        self.host_param = host_param

    def modifyNewPassword(self, password, newpassword):
        cmd = f"echo -e '{password}\n{newpassword}\n{newpassword}\n' | passwd"
        recv_exit_status, _, stdout, stderr = self.conn.exec_command(cmd)

        if recv_exit_status != 0:
            self.mylog.error(f"修改密码：修改失败-{stderr}")
            json_result = {"status": "failed", "msg": f"修改密码失败-{stderr}"}
        else:
            self.mylog.info(f"修改密码：修改成功-{stdout}")
            json_result = {"status": "success", "msg": f"修改密码成功-{stdout}"}

        return json_result

    def checkwd(self, username, password):
        cmd = f"echo '{password}' | su - {username}"
        recv_exit_status, _, stdout, stderr = self.conn.exec_command(cmd)

        # 输出命令执行结果
        if recv_exit_status != 0:
            self.mylog.error(f"检查：主机登录检查失败-{stderr}")
            json_result = {"status": "failed", "msg": f"主机登录检查失败-{stderr}"}
        else:
            self.mylog.info(f"检查：主机登录检查成功-{stdout}")
            json_result = {"status": "success", "msg": "主机登录检查成功"}
        return json_result

    def action(self):
        current_pwd = ""
        new_pwd = ""
        if "current_pwd" in self.action_param:
            current_pwd = self.action_param["current_pwd"]
        if "current_pwd_file" in self.action_param:
            current_pwd = ReadCfg().readcfg(
                os.path.join("config", self.action_param["current_pwd_file"]))[self.hostname]
        if "new_pwd" in self.action_param:
            new_pwd = self.action_param["new_pwd"]
        if "new_pwd_file" in self.action_param:
            new_pwd = ReadCfg().readcfg(os.path.join("config", self.action_param["new_pwd_file"]))[self.hostname]

        if self.action_param["action"] == "modify":
            json_result = self.modifyNewPassword(current_pwd, new_pwd)
        elif self.action_param["action"] == "checknew":
            json_result = self.checkwd(self.host_param["username"], new_pwd)
        elif self.action_param["action"] == "checkcur":
            json_result = self.checkwd(self.host_param["username"], current_pwd)
        else:
            raise Exception('配置文件配置错误:未知action参数' + json.dumps(self.action_param))

        return json_result


