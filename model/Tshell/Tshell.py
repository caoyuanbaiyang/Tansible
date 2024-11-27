# -*- coding: utf-8 -*-

import json
import lib.constants as C

def check_success(mylog, stdout):
    mylog.info(f"检查成功：命令结果-{stdout}")
    json_result = {"status": "success", "msg": f"检查成功-{stdout}"}
    return json_result

def check_failed(mylog, cmd, stdout, check_status):
    mylog.error(
        f'检查失败：命令-{cmd}，命令结果-{stdout}，预期结果-{check_status}')
    json_result = {"status": "failed", "msg": f"检查失败-{stdout}"}
    return json_result

class ModelClass(object):
    def __init__(self, mylog, conn, hostname, action_param, host_param):
        self.mylog = mylog
        self.conn = conn
        self.hostname = hostname
        self.action_param = action_param
        self.host_param = host_param
        self.exec_timeout = self.action_param.get("timeout", C.DEFAULT_COMMAND_EXEC_TIMEOUT)

    def action(self):
        json_result = {}
        if "cmd" not  in self.action_param:
            raise Exception('配置文件配置错误:必须包含cmd配置'.format(param=json.dumps(self.action_param)))
        recv_exit_status, _, stdout, stderr = self.conn.exec_command(self.action_param["cmd"], exec_timeout=self.exec_timeout)

        if recv_exit_status != 0:
            self.mylog.error(f'执行失败：命令-{self.action_param["cmd"]}，错误信息-{stderr}')
            json_result = {"status": "failed", "msg": f"命令执行失败-{stderr}"}
        else:
            self.mylog.debug(f"执行成功：命令结果-{stdout}")
            if "check" not in self.action_param:
                json_result = {"status": "success", "msg": f"命令执行成功-{stdout}"}
            else:
                json_result = self.check(stdout)

        return json_result

    def check(self, stdout):
        json_result = {}

        # check配置只支持int、str类型的检查
        if self.action_param["check"][0] == 'int':
            check_status = int(self.action_param["check"][2].strip())
            try:
                enter_return = int(stdout.strip('\n'))
            except Exception as e:
                self.mylog.error(f'配置错误-{e}')
                raise
            if self.action_param["check"][1].strip() not in ['<', '<=', '==', '>=', '>']:
                self.mylog.error(f'{self.action_param["check"][1]} mismatch !!!')
                raise Exception("配置错误，运算符不匹配")
            elif self.action_param["check"][1].strip() == '<':
                if enter_return < check_status:
                    json_result = check_success(self.mylog, stdout)
                else:
                    json_result = check_failed(self.mylog, self.action_param["cmd"], stdout, check_status)
            elif self.action_param["check"][1].strip() == '<=':
                if enter_return <= check_status:
                    json_result = check_success(self.mylog, stdout)
                else:
                    json_result = check_failed(self.mylog, self.action_param["cmd"], stdout, check_status)
            elif self.action_param["check"][1].strip() == '==':
                if enter_return == check_status:
                    json_result = check_success(self.mylog, stdout)
                else:
                    json_result = check_failed(self.mylog, self.action_param["cmd"], stdout, check_status)
            elif self.action_param["check"][1].strip() == '>=':
                if enter_return >= check_status:
                    json_result = check_success(self.mylog, stdout)
                else:
                    json_result = check_failed(self.mylog, self.action_param["cmd"], stdout, check_status)
            elif self.action_param["check"][1].strip() == '>':
                if enter_return > check_status:
                    json_result = check_success(self.mylog, stdout)
                else:
                    json_result = check_failed(self.mylog, self.action_param["cmd"], stdout, check_status)

        elif self.action_param["check"][0] == 'str':
            check_status = str(self.action_param["check"][2].strip())
            enter_return = str(stdout.strip('\n'))
            enter_return_tail = str(enter_return.split('\n')[-2].strip())
            if self.action_param["check"][1].strip() not in ['==', 'in', 'not in', 'tail ==', 'tail in', 'tail not in']:
                self.mylog.error(f'{self.action_param["check"][1]} mismatch !!!')
                raise Exception("配置错误，运算符不匹配")
            elif self.action_param["check"][1].strip() == '==':
                if enter_return == check_status:
                    json_result = check_success(self.mylog, stdout)
                else:
                    json_result = check_failed(self.mylog, self.action_param["cmd"], stdout, check_status)
            elif self.action_param["check"][1].strip() == 'in':
                if check_status in enter_return:
                    json_result = check_success(self.mylog, stdout)
                else:
                    json_result = check_failed(self.mylog, self.action_param["cmd"], stdout, check_status)
            elif self.action_param["check"][1].strip() == 'not in':
                if check_status not in enter_return:
                    json_result = check_success(self.mylog, stdout)
                else:
                    json_result = check_failed(self.mylog, self.action_param["cmd"], stdout, check_status)
            elif self.action_param["check"][1].strip() == 'tail ==':
                if check_status == enter_return_tail:
                    json_result = check_success(self.mylog, enter_return_tail)
                else:
                    json_result = check_failed(self.mylog, self.action_param["cmd"], stdout, check_status)
            elif self.action_param["check"][1].strip() == 'tail in':
                if check_status in enter_return_tail:
                    json_result = check_success(self.mylog, enter_return_tail)
                else:
                    json_result = check_failed(self.mylog, self.action_param["cmd"], stdout, check_status)
            elif self.action_param["check"][1].strip() == 'tail not in':
                if check_status not in enter_return_tail:
                    json_result = check_success(self.mylog, enter_return_tail)
                else:
                    json_result = check_failed(self.mylog, self.action_param["cmd"], stdout, check_status)
        else:
            self.mylog.error(f'{self.action_param["check"][0]} mismatch !!!')
            raise Exception("配置错误，类型不匹配")

        return json_result
