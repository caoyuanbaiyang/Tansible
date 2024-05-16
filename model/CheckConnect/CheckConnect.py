# -*- coding: utf-8 -*-


class ModelClass(object):
    def __init__(self, mylog, conn, hostname, action_param, host_param):
        self.mylog = mylog

    def action(self):
        self.mylog.info("连接成功")
        return {"status": "success", "msg": "执行成功"}
