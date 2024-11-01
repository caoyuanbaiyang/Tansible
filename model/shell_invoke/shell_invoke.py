# -*- coding: utf-8 -*-

import json
from model.Tshell.Tshell import ModelClass as TshellModelClass

class ModelClass(TshellModelClass):

    def action(self):
        json_result = {}
        if "cmd" not  in self.action_param:
            raise Exception('配置文件配置错误:必须包含cmd配置'.format(param=json.dumps(self.action_param)))
        recv_exit_status, _, stdout, stderr = self.conn.exec_command_invoke_shell(self.action_param["cmd"])

        if recv_exit_status != 0:
            self.mylog.error(f'执行失败：命令-{self.action_param["cmd"]}，错误信息-{stderr}')
            json_result = {"status": "failed", "msg": f"命令执行失败-{stderr}"}
        else:
            self.mylog.debug(f"执行成功：命令结果-{stdout}")
            if "check" not in self.action_param:
                json_result = {"status": "success", "msg": f"命令执行成功-{stdout}"}
                return json_result
            else:
                # check配置只支持int、str类型的检查
                json_result = self.check(stdout)
        return json_result

