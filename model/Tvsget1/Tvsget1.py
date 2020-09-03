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


def generatebigersizefile(filename, content):
    with open(filename, mode='w', encoding='utf-8') as f:
        f.write(content)


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

    def donwload_from_linux(self, sftp, ssh, local_dir, remote_dir, excludes=[], md5filter=0):
        if not isContrainSpecialCharacter(remote_dir):
            if remote_dir.endswith("/"):
                self.sftp_get_dir_exclude(sftp, ssh, local_dir=local_dir, remote_dir=remote_dir, excludes=excludes,
                                          md5filter=md5filter)
            else:
                filesize = sftp.stat(remote_dir).st_size
                self.sftp_get_file_exclude(sftp, ssh, local_dir, remote_dir, excludes, md5filter, filesize)
        else:
            (tmp_remote_dir, filename) = os.path.split(remote_dir)
            for file in sftp.listdir_attr(tmp_remote_dir):
                if match(file.filename, filename):
                    tmp_remote_dir1 = Path(os.path.join(tmp_remote_dir, file.filename)).as_posix()
                    if stat.S_ISDIR(file.st_mode):
                        self.sftp_get_dir_exclude(sftp, ssh, local_dir=local_dir, remote_dir=tmp_remote_dir1,
                                                  excludes=excludes, md5filter=md5filter)
                    else:
                        self.sftp_get_file_exclude(sftp, ssh, local_dir=local_dir, remote_file=tmp_remote_dir1,
                                                   excludes=excludes, md5filter=md5filter, filesize=file.st_size)

    def execcommand(self, ssh, command, stdinfo=[], timeout=5):
        try:
            stdin, stdout, stderr = ssh.exec_command("echo $LANG")
            langset = stdout.readlines()[0].replace("\n", "").split(".")[1]
        except paramiko.ssh_exception.SSHException:
            self.mylog.info("LANG获取失败")
            raise Exception("LANG获取失败")
        try:
            stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
            # self.mylog.info(command)
            for info in stdinfo:
                stdin.write(info + "\n")
                self.mylog.info(info)
            if stderr.readable():
                err = stderr.read()
                err = err.decode(langset)
            if stdout.readable():
                out = stdout.read()
                out = out.decode(langset)
            # self.mylog.info("命令out:"+"".join(out))
        except paramiko.ssh_exception.SSHException:
            # self.mylog.info("命令执行失败:"+command)
            return [False, "命令执行失败:" + command]
        except Exception as e:
            self.mylog.info(e)
            self.mylog.info("命令执行失败:" + command)
            return [False, e]
        if len(err) != 0:
            self.mylog.info("命令err:" + "".join(err))
            return [False, "".join(err)]
        return [True, out]

    def sftp_get_file_exclude(self, sftp, ssh, local_dir, remote_file, excludes=[], md5filter=0, filesize=0):
        (tmp_dir, filename) = os.path.split(remote_file)
        tmp_local_filename = os.path.join(local_dir, filename)
        if not (filename in excludes or remote_file in excludes):
            if filesize > md5filter:
                md5cmd = "md5sum " + remote_file
                content = self.execcommand(ssh, md5cmd)
                self.mylog.info('  Get文件  {} size: {} 传输中...'.format(remote_file, filesize))
                generatebigersizefile(tmp_local_filename, content[1].split()[0])
            else:
                self.mylog.info('  Get文件  %s 传输中...' % remote_file)
                self.mylog.info('   位置  {loc_dir}:'.format(loc_dir=tmp_local_filename))
                try:
                    sftp.get(remote_file, tmp_local_filename)
                except:
                    self.mylog.info("Get文件 {file},{loc} 失败!".format(file=remote_file,
                                                                    loc=tmp_local_filename))

    def sftp_get_dir_exclude(self, sftp, ssh, local_dir, remote_dir, excludes=[], md5filter=0):
        # remote_dir 如果是目录,列出所有目录下的文件及目录循环处理
        for file in sftp.listdir_attr(remote_dir):
            remote_path_filename = Path(os.path.join(remote_dir, file.filename)).as_posix()

            # 如果判断为无需下载的文件，则跳过本次循环，处理下一个文件名词
            if exclude_files(file.filename, remote_path_filename, excludes):
                continue

            # 如果是目录，则递归处理该目录，远端通过stat.S_ISDIR(st_mode)
            if stat.S_ISDIR(file.st_mode):
                tmp_local_dir = os.path.join(local_dir, file.filename)
                if not os.path.exists(tmp_local_dir):
                    os.makedirs(tmp_local_dir)
                self.sftp_get_dir_exclude(sftp, ssh, local_dir=tmp_local_dir, remote_dir=remote_path_filename,
                                          excludes=excludes, md5filter=md5filter)
                self.mylog.info('Get文件夹%s 传输中...' % remote_path_filename)
                self.mylog.info('   位置  {loc_dir}:'.format(loc_dir=tmp_local_dir))
            else:
                # 软连接文件
                # if file.longname.startswith("l") and file.st_size > md5filter:
                if stat.S_ISLNK(file.st_mode) and self.link == "target":
                    self.mylog.info('  Get文件 %s 软连接 传输中...' % remote_path_filename)
                    generatebigersizefile(os.path.join(local_dir, file.filename), sftp.readlink(remote_path_filename))
                    # self.mylog.info(f"{file.filename}  {sftp.readlink(remote_path_filename)}")
                else:
                    self.sftp_get_file_exclude(sftp, ssh, local_dir, remote_path_filename, excludes, md5filter
                                               , file.st_size)

    def __acton_inner(self, sftp, ssh, local_home, cfg_key, cfg_value):
        remote_dir = cfg_value["remote_dir"]
        if "$HOME" in remote_dir:
            remote_dir = remote_dir.replace("$HOME", "/home/"+self.hostparam["username"])
        if not ("exclude" in cfg_value) or cfg_value["exclude"] is None:
            cfg_value["exclude"] = []
        excludes = cfg_value["exclude"]
        md5filter = cfg_value["md5filter"]

        if not ("bigcontent" in cfg_value) or cfg_value["bigcontent"] is None:
            self.bigcontent = ["size", "mtime", "st_mode"]
        else:
            self.bigcontent = cfg_value["bigcontent"]

        if not ("link" in cfg_value) or cfg_value["link"] is None:
            self.link = "target"
        else:
            self.link = cfg_value["link"]

        if cfg_key == "{HOME}":  # 无子目录
            local_dir = local_home
        else:  # 有子目录
            local_dir = os.path.join(local_home, cfg_key)

        if not os.path.exists(local_dir):
            os.makedirs(local_dir)
        self.donwload_from_linux(sftp, ssh, local_dir=local_dir, remote_dir=remote_dir, excludes=excludes,
                                 md5filter=md5filter)

    def action(self, ssh, hostname, param, hostparam=None):
        if hostparam is None:
            hostparam = []
        self.hostparam = hostparam
        if not ("local_dir" in param) or param["local_dir"] is None:
            param["local_dir"] = os.path.join("download", os.path.splitext(os.path.basename(__file__))[0])

        sftp = paramiko.SFTPClient.from_transport(ssh.get_transport())
        for cfg_key, cfg_value in param.items():
            if cfg_key not in ["local_dir"]:
                local_home = os.path.join(param["local_dir"], hostname)
                self.__acton_inner(sftp, ssh, local_home=local_home, cfg_key=cfg_key, cfg_value=cfg_value)

