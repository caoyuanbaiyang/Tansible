# -*- coding: utf-8 -*-

import json
import os



class ModelClass(object):
    def __init__(self, mylog, conn, hostname, action_param, host_param):
        self.mylog = mylog
        self.conn = conn
        self.hostname = hostname
        self.action_param = action_param
        self.host_param = host_param

    def action(self):
        err_list = []
        for cfg_key, cfg_value in self.action_param.items():
            if cfg_key not in ["simple_type", "source_dir", "dest_dir", "exclude"]:
                raise Exception('配置文件配置错误:未知参数:{param}'.format(param=json.dumps(self.action_param)))

        local_dir = self.action_param["source_dir"]
        remote_lst_v = self.action_param["dest_dir"]
        remote_lst = []

        if isinstance(remote_lst_v, list):
            remote_lst = remote_lst_v
        if isinstance(remote_lst_v, str):
            remote_lst.append(remote_lst_v)
        if not isinstance(remote_lst_v, list) and not isinstance(remote_lst_v, str):
            raise Exception('配置文件配置错误:参数dest_dir类型必须是字符串或列表:{param}'.format(
                param=json.dumps(self.action_param)))

        for remote_dir in remote_lst:
            if "$HOME" in remote_dir:
                remote_dir = remote_dir.replace("$HOME", "/home/" + self.host_param["username"])
            if "$USER" in remote_dir:
                remote_dir = remote_dir.replace("$USER", self.host_param["username"])
            if "$HOSTNAME" in remote_dir:
                remote_dir = remote_dir.replace("$HOSTNAME", self.hostname)
            if self.action_param["simple_type"] == 1:
                # 简单方式，目录下面没有主机名文件夹
                if not local_dir.endswith("/"):
                    if remote_dir.endswith("/"):
                        # 本地为文件 目的没有设置文件名
                        (tmp_path, tmp_file) = os.path.split(local_dir)
                        remote_dir = os.path.join(remote_dir, tmp_file)
                    self.mylog.debug(r'  Put文件  %s 传输中...' % local_dir)
                    self.mylog.debug(r'     位置  {file} 传输中...'.format(file=remote_dir))
                    try:
                        self.conn.put_file(local_dir, remote_dir)
                    except:
                        err_list.append(local_dir)
                else:
                    if not self.conn.put_dir(remote_dir=remote_dir, local_dir=local_dir,
                                                     excludes=self.action_param["exclude"])[0]:
                        err_list.append(local_dir)
            elif self.action_param["simple_type"] == 0:
                # 复杂方式，目录下面有主机名文件夹，需要根据主机名文件夹进行上传
                local_dir = os.path.join(self.action_param["source_dir"], self.hostname)
                if not self.conn.put_dir(remote_dir=self.action_param["dest_dir"], local_dir=local_dir,
                                                 excludes=self.action_param["exclude"])[0]:
                    err_list.append(local_dir)
            else:
                raise Exception(
                    '配置文件配置错误:未知simple_type参数:{simple_type}'.format(param=json.dumps(self.action_param)))

        if len(err_list) > 0:
            self.mylog.error(f'执行失败：错误发生在-{err_list}')
            json_result = {"status": "failed", "msg": f"错误发生在-{err_list}"}
        else:
            self.mylog.info(f"执行成功")
            json_result = {"status": "success", "msg": "任务执行成功"}
        return json_result
