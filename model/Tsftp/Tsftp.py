# -*- coding: utf-8 -*-

import json
import os
import stat
from pathlib import Path

import lib.constants as C


class ModelClass(object):
    def __init__(self, mylog, conn, hostname, action_param, host_param):
        self.mylog = mylog
        self.conn = conn
        self.hostname = hostname
        self.action_param = action_param
        self.host_param = host_param

    def download_from_linux(self, local_dir, remote_dir, excludes=None, includes=None):
        if excludes is None:
            excludes = []
        if includes is None:
            includes = []

        return self.sftp_get_dir_exclude(local_dir=local_dir, remote_dir=remote_dir, excludes=excludes)

    def sftp_get_dir_exclude(self, local_dir, remote_dir, excludes=[]):
        err_list = []
        # remote_dir如果是文件
        if not remote_dir.endswith("/"):
            filename = os.path.split(remote_dir)[1]
            if not (filename in excludes or remote_dir in excludes):
                self.mylog.debug('  Get文件  %s 传输中...' % remote_dir)
                self.conn.fetch_file(remote_dir, os.path.join(local_dir, filename))

        # remote_dir 如果是目录,列出所有目录下的文件及目录循环处理
        if remote_dir.endswith("/"):
            for file in self.conn._connect_sftp().listdir_attr(remote_dir):
                remote_path_filename = Path(os.path.join(remote_dir, file.filename)).as_posix()

                # 如果判断为无需下载的文件，则跳过本次循环，处理下一个文件名词
                if C.exclude_files(file.filename, remote_path_filename, excludes):
                    self.mylog.debug('忽略文件%s' % remote_path_filename)
                    continue

                # 如果是目录，则递归处理该目录，远端通过stat.S_ISDIR(st_mode)
                if stat.S_ISDIR(file.st_mode):
                    tmp_local_dir = os.path.join(local_dir, file.filename)
                    if not os.path.exists(tmp_local_dir):
                        os.makedirs(tmp_local_dir)
                    self.sftp_get_dir_exclude(local_dir=tmp_local_dir, remote_dir=remote_path_filename + "/",
                                              excludes=excludes)
                    self.mylog.debug('Get文件夹%s 传输中...' % remote_path_filename)
                    self.mylog.debug('   位置  {loc_dir}:'.format(loc_dir=tmp_local_dir))
                else:
                    tmp_local_filename = os.path.join(local_dir, file.filename)
                    try:
                        self.mylog.debug('  Get文件  %s 传输中...' % remote_path_filename)
                        self.mylog.debug('   位置  {loc_dir}:'.format(loc_dir=tmp_local_filename))
                        self.conn.fetch_file(remote_path_filename, tmp_local_filename)
                    except Exception as e:
                        self.mylog.error(
                            f"Get文件 {remote_path_filename},{tmp_local_filename} 失败! msg-{e}")
                        err_list.append(remote_path_filename)
        if len(err_list) > 0:
            return False
        return True

    def sftp_put_dir_exclude(self, remote_dir, local_dir, excludes=[]):
        err_list = []
        for file in os.listdir(local_dir):
            # local_dir目录中每一个文件或目录的完整路径
            loc_path_filename = os.path.join(local_dir, file)
            if C.exclude_files(file, loc_path_filename, excludes):
                continue

            # 如果是目录，则递归处理该目录
            if os.path.isdir(loc_path_filename):
                rmt_dir = Path(os.path.join(remote_dir, file)).as_posix()
                try:
                    self.conn._connect_sftp().mkdir(rmt_dir)
                except:
                    pass
                self.mylog.debug(r'Put文件夹 %s 传输中...' % loc_path_filename)
                self.sftp_put_dir_exclude(remote_dir=rmt_dir, local_dir=loc_path_filename, excludes=excludes)
            else:
                remote_filename = Path(os.path.join(remote_dir, file)).as_posix()
                self.mylog.debug(r'  Put文件  %s 传输中...' % loc_path_filename)
                self.mylog.debug(r'     位置  {file} 传输中...'.format(file=remote_filename))
                try:
                    self.conn.put_file(loc_path_filename, remote_filename)
                except:
                    err_list.append(loc_path_filename)

        if len(err_list) > 0:
            return False
        return True

    def __acton_inner(self, local_home, cfg_key, cfg_value, action, hostname=None):
        remote_dir = cfg_value["remote_dir"]
        if "$HOME" in remote_dir:
            remote_dir = remote_dir.replace("$HOME", "/home/" + self.host_param["username"])
        if "$USER" in remote_dir:
            remote_dir = remote_dir.replace("$USER", self.host_param["username"])
        if "$HOSTNAME" in remote_dir:
            remote_dir = remote_dir.replace("$HOSTNAME", hostname)

        if not ("exclude" in cfg_value) or cfg_value["exclude"] is None:
            cfg_value["exclude"] = []
        excludes = cfg_value["exclude"]

        if not ("include" in cfg_value) or cfg_value["include"] is None:
            cfg_value["include"] = []
        includes = cfg_value["include"]

        if cfg_key in ["{HOME}", "NO_DIR"]:  # 无子目录
            local_dir = local_home
        else:  # 有子目录
            local_dir = os.path.join(local_home, cfg_key)
        if action == "download":
            if not os.path.exists(local_dir):
                os.makedirs(local_dir)
            return self.download_from_linux(local_dir=local_dir, remote_dir=remote_dir,
                                            excludes=excludes, includes=includes)
        if action == "upload":
            if not remote_dir.endswith("/"):
                (remote_dir, tmp_filename) = os.path.split(remote_dir)
            return self.sftp_put_dir_exclude(local_dir=local_dir, remote_dir=remote_dir, excludes=excludes)

    def action(self):
        err_list = []
        if self.action_param["action"] not in ["download", "upload"]:
            raise Exception(
                '配置文件配置错误:未知action参数:{action}'.format(action=json.dumps(self.action_param["action"])))

        if not ("local_dir" in self.action_param) or self.action_param["local_dir"] is None:
            self.action_param["local_dir"] = os.path.join("download", os.path.splitext(os.path.basename(__file__))[0])

        for cfg_key, cfg_value in self.action_param.items():
            if cfg_key not in ["action", "local_dir"]:
                local_home = os.path.join(self.action_param["local_dir"], self.hostname)
                if not self.__acton_inner(local_home=local_home, cfg_key=cfg_key, cfg_value=cfg_value,
                                          action=self.action_param["action"], hostname=self.hostname):
                    err_list.append(cfg_key)

        if len(err_list) > 0:
            self.mylog.error(f'执行失败：错误发生在-{err_list}')
            json_result = {"status": "failed", "msg": f"错误发生在-{err_list}"}
        else:
            self.mylog.info(f"执行成功")
            json_result = {"status": "success", "msg": "任务执行成功"}
        return json_result
