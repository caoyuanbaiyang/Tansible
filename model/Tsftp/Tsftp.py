# -*- coding: utf-8 -*-
from lib.tools import Tools
import json
import os
import stat
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

    def donwload_from_linux(self, sftp, local_dir, remote_dir, excludes=None, includes=None):
        if excludes is None:
            excludes = []
        if includes is None:
            includes = []

        if not isContrainSpecialCharacter(remote_dir):
            # 只有在remote dir 为文件夹（以/结尾）时，才支持include设置
            if remote_dir.endswith("/") and len(includes) > 0:
                for include in includes:
                    self.sftp_get_dir_exclude(sftp, os.path.join(local_dir, include),
                                              os.path.join(remote_dir, include) + "/", excludes)
            else:
                self.sftp_get_dir_exclude(sftp, local_dir=local_dir, remote_dir=remote_dir, excludes=excludes)
        else:
            (tmp_remote_dir, filename) = os.path.split(remote_dir)
            for file in sftp.listdir_attr(tmp_remote_dir):
                if match(file.filename, filename):
                    tmp_remote_dir1 = Path(os.path.join(tmp_remote_dir, file.filename)).as_posix()
                    if stat.S_ISDIR(file.st_mode):
                        tmp_remote_dir1 = tmp_remote_dir1 + "/"
                    self.sftp_get_dir_exclude(sftp, local_dir=local_dir, remote_dir=tmp_remote_dir1, excludes=excludes)

    def sftp_get_dir_exclude(self, sftp, local_dir, remote_dir, excludes=[]):
        # remote_dir如果是文件
        if not remote_dir.endswith("/"):
            (tmp_dir, filename) = os.path.split(remote_dir)
            if not (filename in excludes or remote_dir in excludes):
                self.mylog.info('  Get文件  %s 传输中...' % remote_dir)
                sftp.get(remote_dir, os.path.join(local_dir, filename))

        # remote_dir 如果是目录,列出所有目录下的文件及目录循环处理
        if remote_dir.endswith("/"):
            # print(remote_dir)
            for file in sftp.listdir_attr(remote_dir):
                # debug

                # if file == "temp":
                #     print(file)
                # debug
                remote_path_filename = Path(os.path.join(remote_dir, file.filename)).as_posix()

                # 如果判断为无需下载的文件，则跳过本次循环，处理下一个文件名词
                if exclude_files(file.filename, remote_path_filename, excludes):
                    self.mylog.info('忽略文件%s' % remote_path_filename)
                    continue

                # 如果是目录，则递归处理该目录，远端通过stat.S_ISDIR(st_mode)
                if stat.S_ISDIR(file.st_mode):
                    tmp_local_dir = os.path.join(local_dir, file.filename)
                    if not os.path.exists(tmp_local_dir):
                        os.makedirs(tmp_local_dir)
                    self.sftp_get_dir_exclude(sftp, local_dir=tmp_local_dir, remote_dir=remote_path_filename + "/",
                                              excludes=excludes)
                    self.mylog.info('Get文件夹%s 传输中...' % remote_path_filename)
                    self.mylog.info('   位置  {loc_dir}:'.format(loc_dir=tmp_local_dir))
                else:
                    tmp_local_filename = os.path.join(local_dir, file.filename)
                    try:
                        self.mylog.info('  Get文件  %s 传输中...' % remote_path_filename)
                        self.mylog.info('   位置  {loc_dir}:'.format(loc_dir=tmp_local_filename))
                        sftp.get(remote_path_filename, tmp_local_filename)
                    except:
                        self.mylog.info(
                            "Get文件 {file},{loc} 失败!".format(file=remote_path_filename, loc=tmp_local_filename))
                        # self.mylog.info("Get文件  {file} 失败".format(host=hostname, file=remote_file))

    def __acton_inner(self, sftp, local_home, cfg_key, cfg_value, action):
        remote_dir = cfg_value["remote_dir"]
        if "$HOME" in remote_dir:
            remote_dir = remote_dir.replace("$HOME", "/home/" + self.hostparam["username"])
        if not ("exclude" in cfg_value) or cfg_value["exclude"] is None:
            cfg_value["exclude"] = []
        excludes = cfg_value["exclude"]

        if not ("include" in cfg_value) or cfg_value["include"] is None:
            cfg_value["include"] = []
        includes = cfg_value["include"]

        if cfg_key == "{HOME}":  # 无子目录
            local_dir = local_home
        else:  # 有子目录
            local_dir = os.path.join(local_home, cfg_key)
        if action == "download":
            if not os.path.exists(local_dir):
                os.makedirs(local_dir)
            self.donwload_from_linux(sftp, local_dir=local_dir, remote_dir=remote_dir,
                                     excludes=excludes, includes=includes)
        if action == "upload":
            if not remote_dir.endswith("/"):
                (remote_dir, tmp_filename) = os.path.split(remote_dir)
            self.sftp_put_dir_exclude(sftp, local_dir=local_dir, remote_dir=remote_dir, excludes=excludes)

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
                self.mylog.info(r'     位置  {file} 传输中...'.format(file=remote_filename))
                sftp.put(loc_path_filename, remote_filename)

    def action(self, ssh, hostname, param, hostparam=None):
        if hostparam is None:
            hostparam = []
        self.hostparam = hostparam
        if param["action"] not in ["download", "upload"]:
            raise Exception('配置文件配置错误:未知action参数:{action}'.format(action=json.dumps(param["action"])))

        if not ("local_dir" in param) or param["local_dir"] is None:
            param["local_dir"] = os.path.join("download", os.path.splitext(os.path.basename(__file__))[0])

        sftp = paramiko.SFTPClient.from_transport(ssh.get_transport())
        for cfg_key, cfg_value in param.items():
            if cfg_key not in ["action", "local_dir"]:
                local_home = os.path.join(param["local_dir"], hostname)
                self.__acton_inner(sftp, local_home=local_home, cfg_key=cfg_key, cfg_value=cfg_value,
                                   action=param["action"])
