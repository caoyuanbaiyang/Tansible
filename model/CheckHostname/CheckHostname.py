# -*- coding: utf-8 -*-


class ModelClass(object):
    def __init__(self, mylog, conn, hostname, action_param, host_param):
        self.mylog = mylog
        self.conn = conn
        self.hostname = hostname
        self.action_param = action_param
        self.host_param = host_param

    def check_hostname(self):
        cmd = self.action_param["cmd"]
        recv_exit_status, _, stdout, stderr = self.conn.exec_command(cmd)
        self.mylog.debug(f"recv_exit_status:{recv_exit_status}, stdout:{stdout}, stderr:{stderr} ")
        cmd_hostname = stdout.rstrip('\n')
        if cmd_hostname == self.hostname:
            return True, cmd_hostname
        else:
            return False, cmd_hostname

    def action(self):

        if self.action_param is None or "cmd" not in self.action_param.keys():
            param = {"cmd": "hostname"}
        rz, cmd_hostname = self.check_hostname()

        if rz:
            self.mylog.info("主机名检查--成功")
            json_result = {"status": "success", "msg": "主机名检查成功"}
        else:
            self.mylog.error(f"主机名检查--失败 cfg:{self.hostname} result:{cmd_hostname}")
            json_result = {"status": "failed", "msg": f"主机名检查失败，cfg:{self.hostname} result:{cmd_hostname}"}
        return json_result
