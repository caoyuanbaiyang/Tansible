# -*- coding: utf-8 -*-

import json
import os
import paramiko
from pathlib import Path
from fnmatch import fnmatchcase as match


def isContrainSpecialCharacter(string):
    # fnmatch 支持的模糊匹配通配符
    special_character = r"*?[]!"
    for i in special_character:
        if i in string:
            return True
    return False


def exclude_files(filename, dir_filename, excludes=[]):  # 是否属于不下载的文件判断
    # exclude 为具体配置，支持文件名配置及带目录的配置   # exclude 的不下载，跳过本次循环，进入下一循环
    if filename in excludes or dir_filename in excludes:
        return True

    # exclude 为模糊配置，配置的话就不下载，跳过本次循环，进入下一循环
    for exclude in excludes:
        if match(filename, exclude) or match(dir_filename, exclude):
            return True

    # 跳过隐藏文件的下载，但是.bash_profile  .bashrc 包含环境信息，需要下载
    if filename in [".bash_history", ".bash_logout", ".ssh", ".viminfo", ".pki"]:
        return True
    # 以上情况都不是这返回False
    return False


class ModelClass(object):
    def __init__(self, mylog):
        self.mylog = mylog

    def sftp_put_dir_exclude(self, sftp, remote_dir, local_dir, excludes=[]):
        for file in os.listdir(local_dir):
            # local_dir目录中每一个文件或目录的完整路径
            loc_path_filename = os.path.join(local_dir, file)
            if exclude_files(file, loc_path_filename, excludes):
                continue

            # 如果是目录，则递归处理该目录
            if os.path.isdir(loc_path_filename):
                rmt_dir = Path(os.path.join(remote_dir, file)).as_posix()
                try:
                    sftp.mkdir(rmt_dir)
                except:
                    pass
                self.mylog.info(r'Put文件夹 %s 传输中...' % loc_path_filename)
                self.sftp_put_dir_exclude(sftp, remote_dir=rmt_dir, local_dir=loc_path_filename, excludes=excludes)
            else:
                remote_filename = Path(os.path.join(remote_dir, file)).as_posix()
                self.mylog.info(r'  Put文件  %s 传输中...' % loc_path_filename)
                self.mylog.info(r'     位置  {file} 传输中...' .format(file=remote_filename))
                sftp.put(loc_path_filename, remote_filename)

    def action(self, ssh, hostname, param, hostparam=None):
        if hostparam is None:
            hostparam = []
        sftp = paramiko.SFTPClient.from_transport(ssh.get_transport())
        for cfg_key, cfg_value in param.items():
            if cfg_key not in ["simple_type", "source_dir", "dest_dir", "exclude"]:
                raise Exception('配置文件配置错误:未知参数:{param}'.format(param=json.dumps(param)))

        local_dir = param["source_dir"]
        remote_dir = param["dest_dir"]
        if param["simple_type"] == 1:
            # 简单方式，目录下面没有主机名文件夹
            if not local_dir.endswith("/"):
                if remote_dir.endswith("/"):
                    # 本地为文件 目的没有设置文件名
                    (tmp_path, tmp_file) = os.path.split(local_dir)
                    remote_dir = os.path.join(remote_dir, tmp_file)
                self.mylog.info(r'  Put文件  %s 传输中...' % local_dir)
                self.mylog.info(r'     位置  {file} 传输中...'.format(file=remote_dir))
                sftp.put(local_dir, remote_dir)
            else:
                self.sftp_put_dir_exclude(sftp, remote_dir=param["dest_dir"], local_dir=param["source_dir"],
                                          excludes=param["exclude"])
        elif param["simple_type"] == 0:
            # 复杂方式，目录下面有主机名文件夹，需要根据主机名文件夹进行上传
            local_dir = os.path.join(param["source_dir"], hostname)
            self.sftp_put_dir_exclude(sftp, remote_dir=param["dest_dir"], local_dir=local_dir,
                                      excludes=param["exclude"])
        else:
            raise Exception('配置文件配置错误:未知simple_type参数:{simple_type}'.format(param=json.dumps(param)))
