# -*- coding: utf-8 -*-

from lib.tools import Tools
import paramiko
import os
import shutil
import datetime
import json

now_time = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
down_dir = r"download\dbpwdmodify"
down_dir_bak = down_dir + now_time


class ModelClass(object):
    def __init__(self, mylog):
        self.mylog = mylog

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

    def __acton_inner(self, sftp, hostname, svr_name, cfg_item, ctype):
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
                sftp.get(remote_file, local_file)
                # 备份文件，方便对比及回滚
                shutil.copy(local_file, bak_file)
            except:
                self.mylog.error("文件下载失败{host}:{file}".format(host=hostname, file=remote_file))
            else:
                self.mylog.info('Get文件 {host}:{file} 传输完成...'.format(host=hostname, file=remote_file))
                # 修改密码
                self.change_pwd_cfg(local_file, cfg_item)
        else:
            try:
                if ctype == "UPLOAD":
                    sftp.put(local_file, remote_file)
                if ctype == "ROLLBACK":
                    sftp.put(bak_file, remote_file)
            except:
                if ctype == "UPLOAD":
                    self.mylog.error("文件上传失败{host}:{file}".format(host=hostname, file=remote_file))
                if ctype == "ROLLBACK":
                    self.mylog.error("文件上传失败{host}:{file}".format(host=hostname, file=bak_file))
            else:
                self.mylog.info('Put文件 %s:%s 传输完成...' % (hostname, remote_file))

    def action(self, ssh, hostname, param, hostparam=None):
        if hostparam is None:
            hostparam = []
        for task in param["action"]:
            if task in ["DOWNLOAD", "UPLOAD", "ROLLBACK"]:
                sftp = paramiko.SFTPClient.from_transport(ssh.get_transport())
                for srv_name, cfg_item in param.items():
                    if srv_name != "action":
                        self.__acton_inner(sftp, hostname, srv_name, cfg_item, task)
            else:
                raise Exception('配置文件配置错误:未知action参数' + json.dumps(param))


if __name__ == '__main__':
    pass
