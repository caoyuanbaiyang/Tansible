# -*- coding: utf-8 -*-

import os
import shutil
import datetime
import json

now_time = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
down_dir = r"download\dbpwdmodify"
down_dir_bak = down_dir + now_time


class ModelClass(object):
    def __init__(self, mylog, conn, hostname, action_param, host_param):
        self.mylog = mylog
        self.conn = conn
        self.hostname = hostname
        self.action_param = action_param
        self.host_param = host_param

    def change_pwd_cfg(self, file, cfgitem):
        # 修改密码
        with open(file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        with open(file, "w", encoding="utf-8", newline='') as f_w:
            for line in lines:
                line = line.strip()
                if cfgitem["instr"] in line and line[0] != '#':
                    line = cfgitem["instr"] + cfgitem["pwd"]
                f_w.write(line + '\n')

    def __acton_inner(self, hostname, svr_name, cfg_item, ctype):
        result = True  # True 表示正确， False 表示有错误
        remote_file = cfg_item["cfg_file"]
        (tmppath, filename) = os.path.split(remote_file)
        if not os.path.exists(os.path.join(down_dir, hostname, svr_name)):
            os.makedirs(os.path.join(down_dir, hostname, svr_name))
        # 下载文件名称
        local_file = os.path.join(down_dir, hostname, svr_name, filename)
        # 备份文件名称
        bak_file = local_file + "_bak"
        if ctype == "DOWNLOAD":
            try:
                self.conn.fetch_file(remote_file, local_file)
                # 备份文件，方便对比及回滚
                shutil.copy(local_file, bak_file)
            except:
                self.mylog.error("文件下载失败{host}:{file}".format(host=hostname, file=remote_file))
                result = False
            else:
                self.mylog.debug('Get文件 {host}:{file} 传输完成...'.format(host=hostname, file=remote_file))
                # 修改密码
                self.change_pwd_cfg(local_file, cfg_item)
        else:
            try:
                if ctype == "UPLOAD":
                    self.conn.put_file(local_file, remote_file)
                if ctype == "ROLLBACK":
                    self.conn.put_file(bak_file, remote_file)
            except:
                result = False
                if ctype == "UPLOAD":
                    self.mylog.error("文件上传失败{host}:{file}".format(host=hostname, file=remote_file))
                if ctype == "ROLLBACK":
                    self.mylog.error("文件上传失败{host}:{file}".format(host=hostname, file=bak_file))
            else:
                self.mylog.debug('Put文件 %s:%s 传输完成...' % (hostname, remote_file))
        return result

    def action(self):
        err_list = []
        for task in self.action_param["action"]:
            if task in ["DOWNLOAD", "UPLOAD", "ROLLBACK"]:
                for srv_name, cfg_item in self.action_param.items():
                    if srv_name != "action":
                        if not self.__acton_inner(self.hostname, srv_name, cfg_item, task):
                            err_list.append(srv_name)
            else:
                raise Exception('配置文件配置错误:未知action参数fghfghbn' + json.dumps(self.action_param))

        if len(err_list) > 0:
            self.mylog.error(f'执行失败：错误发生在-{err_list}')
            json_result = {"status": "failed", "msg": f"错误发生在-{err_list}"}
        else:
            self.mylog.info(f"执行成功")
            json_result = {"status": "success", "msg": "任务执行成功"}
        return json_result


if __name__ == '__main__':
    pass
