# -*- coding: utf-8 -*-

import json


class ModelClass(object):
    def __init__(self, mylog, conn, hostname, action_param, host_param):
        self.mylog = mylog
        self.conn = conn
        self.hostname = hostname
        self.action_param = action_param
        self.host_param = host_param

    def action(self):
        for cfg_key, cfg_value in self.action_param.items():
            if cfg_key not in ["cmd"]:
                raise Exception('配置文件配置错误:未知参数:{param}'.format(param=json.dumps(self.action_param)))
        recv_exit_status, _, stdout, stderr = self.conn.exec_command(self.action_param["cmd"])

        if recv_exit_status != 0:
            self.mylog.error(f'执行失败：命令-{self.action_param["cmd"]}，错误信息-{stderr}')
            json_result = {"status": "failed", "msg": f"命令执行失败-{stderr}"}
        else:
            self.mylog.info(f"执行成功：命令执行成功-{stdout}")
            json_result = {"status": "success", "msg": f"命令执行成功-{stdout}"}

        return json_result
