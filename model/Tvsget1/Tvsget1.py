# -*- coding: utf-8 -*-

import os
import stat
from pathlib import Path
from fnmatch import fnmatchcase as match

import lib.constants as C


def generatebigersizefile(filename, content):
    with open(filename, mode='w', encoding='utf-8') as f:
        f.write(content)


class ModelClass(object):
    def __init__(self, mylog, conn, hostname, action_param, host_param):
        self.mylog = mylog
        self.conn = conn
        self.hostname = hostname
        self.action_param = action_param
        self.host_param = host_param

        self.bigcontent = None
        self.link = None

    def download_from_linux(self, local_dir, remote_dir, excludes=[], md5filter=0):
        err_list = []
        # remote_dir 支持模糊匹配，目录配置必须以“/”结尾
        if not C.isContrainSpecialCharacter(remote_dir):
            if remote_dir.endswith("/"):
                if not self.sftp_get_dir_exclude(local_dir=local_dir, remote_dir=remote_dir, excludes=excludes,
                                                 md5filter=md5filter):
                    err_list.append(f"{self.hostname}:{remote_dir}")
            else:
                if not self.sftp_get_file_exclude(local_dir, remote_dir, excludes, md5filter):
                    err_list.append(f"{self.hostname}:{remote_dir}")
        else:
            (tmp_remote_dir, filename) = os.path.split(remote_dir)
            for file in self.conn._connect_sftp().listdir_attr(tmp_remote_dir):
                if match(file.filename, filename):
                    tmp_remote_dir1 = Path(os.path.join(tmp_remote_dir, file.filename)).as_posix()
                    if stat.S_ISDIR(file.st_mode):
                        if not self.sftp_get_dir_exclude(local_dir=local_dir, remote_dir=tmp_remote_dir1,
                                                         excludes=excludes, md5filter=md5filter):
                            err_list.append(f"{self.hostname}:{tmp_remote_dir1}")
                    else:
                        if not self.sftp_get_file_exclude(local_dir=local_dir, remote_file=tmp_remote_dir1,
                                                          excludes=excludes, md5filter=md5filter):
                            err_list.append(f"{self.hostname}:{tmp_remote_dir1}")

        if len(err_list) > 0:
            return False  # 表示有错误
        return True  # 表示没有错误

    def execcommand(self, command):
        recv_exit_status, _, stdout, stderr = self.conn.exec_command(command)
        return stdout.rtrip('\n')

    def sftp_get_file_exclude(self, local_dir, remote_file, excludes=[], md5filter=0):
        result = True  # False 表示有错误，Ture表示正常
        (tmp_dir, filename) = os.path.split(remote_file)
        tmp_local_filename = os.path.join(local_dir, filename)
        filesize = self.conn._connect_sftp().stat(remote_file).st_size
        if filename in excludes or remote_file in excludes:
            self.mylog.debug('  跳过文件  {}'.format(remote_file))
            return True
        if filesize > md5filter:
            md5cmd = "md5sum " + remote_file
            content = self.execcommand(md5cmd)
            self.mylog.debug('  Get文件  {} size: {} 传输中...'.format(remote_file, filesize))
            try:
                generatebigersizefile(tmp_local_filename, content[1].split()[0])
            except:
                result = False
        else:
            self.mylog.debug('  Get文件  %s 传输中...' % remote_file)
            self.mylog.debug('   位置  {loc_dir}:'.format(loc_dir=tmp_local_filename))
            try:
                self.conn.fetch_file(remote_file, tmp_local_filename)
            except:
                result = False
                self.mylog.debug("Get文件 {file},{loc} 失败!".format(file=remote_file,
                                                                     loc=tmp_local_filename))
        return result

    def sftp_get_dir_exclude(self, local_dir, remote_dir, excludes=[], md5filter=0):
        err_list = []
        # remote_dir 如果是目录,列出所有目录下的文件及目录循环处理
        for file in self.conn._connect_sftp().listdir_attr(remote_dir):
            remote_path_filename = Path(os.path.join(remote_dir, file.filename)).as_posix()

            # 如果判断为无需下载的文件，则跳过本次循环，处理下一个文件名词
            if C.exclude_files(file.filename, remote_path_filename, excludes):
                continue

            # 如果是目录，则递归处理该目录，远端通过stat.S_ISDIR(st_mode)
            if stat.S_ISDIR(file.st_mode):
                tmp_local_dir = os.path.join(local_dir, file.filename)
                if not os.path.exists(tmp_local_dir):
                    os.makedirs(tmp_local_dir)
                self.sftp_get_dir_exclude(local_dir=tmp_local_dir, remote_dir=remote_path_filename,
                                          excludes=excludes, md5filter=md5filter)
                self.mylog.debug('Get文件夹%s 传输中...' % remote_path_filename)
                self.mylog.debug('   位置  {loc_dir}:'.format(loc_dir=tmp_local_dir))
            else:
                # 软连接文件
                if stat.S_ISLNK(file.st_mode) and self.link == "target":
                    self.mylog.debug('  Get文件 %s 软连接 传输中...' % remote_path_filename)
                    try:
                        generatebigersizefile(os.path.join(local_dir, file.filename),
                                              self.conn._connect_sftp().readlink(remote_path_filename))
                    except Exception as e:
                        self.mylog.error('  Get文件 %s 软连接 传输失败...' % remote_path_filename)
                        err_list.append(remote_path_filename)
                # 普通文件
                else:
                    if not self.sftp_get_file_exclude(local_dir, remote_path_filename, excludes, md5filter):
                        err_list.append(remote_path_filename)

        if len(err_list) > 0:
            return False  # 表示有错误
        return True  # 表示没有错误

    def __acton_inner(self, local_home, cfg_key, cfg_value):
        remote_dir = cfg_value["remote_dir"]
        if "$HOME" in remote_dir:
            remote_dir = remote_dir.replace("$HOME", "/home/" + self.host_param["username"])
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

        if cfg_key in ["{HOME}", "NO_DIR"]:  # 无子目录
            local_dir = local_home
        else:  # 有子目录
            local_dir = os.path.join(local_home, cfg_key)

        if not os.path.exists(local_dir):
            os.makedirs(local_dir)
        return self.download_from_linux(local_dir=local_dir, remote_dir=remote_dir, excludes=excludes,
                                        md5filter=md5filter)

    def action(self):
        err_list = []
        if not ("local_dir" in self.action_param) or self.action_param["local_dir"] is None:
            self.action_param["local_dir"] = os.path.join("download", os.path.splitext(os.path.basename(__file__))[0])

        for cfg_key, cfg_value in self.action_param.items():
            if cfg_key not in ["local_dir"]:
                local_home = os.path.join(self.action_param["local_dir"], self.hostname)
                if not self.__acton_inner(local_home=local_home, cfg_key=cfg_key, cfg_value=cfg_value):
                    err_list.append(cfg_key)

        if len(err_list) > 0:
            self.mylog.error(f'执行失败：错误发生在-{err_list}')
            json_result = {"status": "failed", "msg": f"错误发生在-{err_list}"}
        else:
            self.mylog.info(f"执行成功")
            json_result = {"status": "success", "msg": "任务执行成功"}
        return json_result
