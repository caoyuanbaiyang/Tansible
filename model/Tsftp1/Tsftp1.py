# -*- coding: utf-8 -*-
import glob
import stat
import json
import os
from pathlib import Path


class ModelClass(object):
    def __init__(self, mylog, conn, hostname, action_param, host_param):
        self.mylog = mylog
        self.conn = conn
        self.hostname = hostname
        self.action_param = action_param
        self.host_param = host_param

    def _resolve_remote_wildcard(self, remote_path):
        """解析远程路径中的通配符，返回匹配的文件列表"""
        if '*' not in remote_path:
            return [remote_path]

        # 分离目录和通配符模式
        remote_dir = os.path.dirname(remote_path)
        pattern = os.path.basename(remote_path)

        # 通过SSH执行ls命令匹配通配符
        cmd = f"ls -d {remote_dir}/{pattern}"
        exit_status, _, stdout, stderr = self.conn.exec_command(cmd)

        if exit_status != 0:
            self.mylog.warning(f"No remote files matched pattern: {remote_path}")
            return []

        # 处理返回结果，过滤空行和错误信息
        files = [line.strip() for line in stdout.split() if line.strip()]
        return [os.path.join(remote_dir, f) for f in files]

    def _resolve_local_wildcard(self, local_path):
        """解析本地路径中的通配符，返回匹配的文件列表"""
        if '*' not in local_path:
            return [local_path]

        return glob.glob(local_path)

    def download_from_linux(self, local_dir, remote_dir, excludes=None):
        result_bool = False
        err_list = []
        if excludes is None:
            excludes = []

        # 解析远程通配符路径
        remote_paths = self._resolve_remote_wildcard(remote_dir)
        for remote_path in remote_paths:
            # 检查是否为目录
            try:
                file_attr = self.conn._connect_sftp().stat(remote_path)
            except Exception as e:
                self.mylog.error(f"无法获取远程路径信息: {remote_path}, 错误: {str(e)}")
                err_list.append(remote_path)
                continue

            # 如果是目录，使用原逻辑递归处理
            if stat.S_ISDIR(file_attr.st_mode):
                dir_name = Path(remote_path).name
                # 如果本地目录不存在则创建
                local_path = Path(local_dir)/dir_name
                if not os.path.exists(local_path):
                    os.makedirs(local_path)
                # 递归处理目录
                result_bool, err_list = self.conn.fetch_dir(local_dir=local_path, remote_dir=remote_path,
                                                            excludes=excludes)
            # 如果是文件，
            else:
                filename = Path(remote_path).name
                if not (filename in excludes or remote_path in excludes):
                    self.mylog.debug('  Get文件  %s 传输中...' % remote_path)
                    self.conn.fetch_file(remote_path, Path(local_dir)/filename)

        return result_bool, err_list

    def upload_to_linux(self, remote_dir, local_dir, excludes=None):
        if excludes is None:
            excludes = []
        return self.conn.put_dir(remote_dir, local_dir, excludes)

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

        # 暂时不支持include 选项
        # if not ("include" in cfg_value) or cfg_value["include"] is None:
        #     cfg_value["include"] = []
        # includes = cfg_value["include"]

        if cfg_key in ["{HOME}", "NO_DIR"]:  # 无子目录
            local_dir = local_home
        else:  # 有子目录
            # local_dir local_home download/Tsftp/hostname 目录再拼接配置项目如conf 则为download/Tsftp/hostname/conf
            local_dir = os.path.join(local_home, cfg_key)
        if action == "download":
            if not os.path.exists(local_dir):
                os.makedirs(local_dir)
            # local_dir 为
            return self.download_from_linux(local_dir=local_dir, remote_dir=remote_dir, excludes=excludes)
        if action == "upload":
            # acion 为upload 则 remote_dir 必须配置为目录，即以“/”结尾，否则进行以下的处理
            if not remote_dir.endswith("/"):
                (remote_dir, tmp_filename) = os.path.split(remote_dir)
            return self.upload_to_linux(local_dir=local_dir, remote_dir=remote_dir, excludes=excludes)

    def action(self):
        err_list = []
        if self.action_param["action"] not in ["download", "upload"]:
            raise Exception(
                '配置文件配置错误:未知action参数:{action}'.format(action=json.dumps(self.action_param["action"])))

        # local_dir为可选配置项，不配置则默认在download/Tsftp目录下
        if not ("local_dir" in self.action_param) or self.action_param["local_dir"] is None:
            self.action_param["local_dir"] = os.path.join("download", os.path.splitext(os.path.basename(__file__))[0])

        for cfg_key, cfg_value in self.action_param.items():
            if cfg_key not in ["action", "local_dir"]:
                # local_home为download/Tsftp/hostname 目录
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
