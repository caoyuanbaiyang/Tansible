# -*- coding: utf-8 -*-

import json

def check_success(mylog, stdout):
    mylog.info(f"检查成功：命令结果-{stdout}")
    json_result = {"status": "success", "msg": f"命令执行成功-{stdout}"}
    return json_result

def check_failed(mylog, cmd, stdout, check_status):
    mylog.error(
        f'检查失败：命令-{cmd}，命令结果-{stdout}，预期结果-{check_status}')
    json_result = {"status": "failed", "msg": f"命令执行失败-{stdout}"}
    return json_result

class ModelClass(object):
    def __init__(self, mylog, conn, hostname, action_param, host_param):
        self.mylog = mylog
        self.conn = conn
        self.hostname = hostname
        self.action_param = action_param
        self.host_param = host_param

    def action(self):
        json_result = {}
        if "cmd" not  in self.action_param:
            raise Exception('配置文件配置错误:必须包含cmd配置'.format(param=json.dumps(self.action_param)))
        recv_exit_status, _, stdout, stderr = self.conn.exec_command(self.action_param["cmd"])

        if recv_exit_status != 0:
            self.mylog.error(f'执行失败：命令-{self.action_param["cmd"]}，错误信息-{stderr}')
            json_result = {"status": "failed", "msg": f"命令执行失败-{stderr}"}
            return json_result

        # 没有check配置，直接返回结果
        if "check" not in self.action_param:
            self.mylog.info(f"执行成功：命令执行成功-{stdout}")
            json_result = {"status": "success", "msg": f"命令执行成功-{stdout}"}
            return json_result

        # 有check配置，返回结果还需跟check配置进行比较
        if "check" in self.action_param:
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
                if self.action_param["check"][1].strip() not in ['==','in', 'not in']:
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
            else:
                self.mylog.error(f'{self.action_param["check"][0]} mismatch !!!')
                raise Exception("配置错误，类型不匹配")

        return json_result
