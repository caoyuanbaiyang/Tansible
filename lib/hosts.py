#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2020/5/7 7:34
# @Author  : TYQ
# @File    : hosts.py.py
# @Software: win10 python3
import re

PATTERN_WITH_SUBSCRIPT = re.compile(
    r'''^
        (.+)                    # A pattern expression ending with...
        \[                    # A [subscript] expression comprising:            
            ([0-9]+)([:])      # Or an x:y or x: range.
            ([0-9]+)
        \]
        $
    ''', re.X
)


class hosts(object):
    def __init__(self, mylog, groups, cfghosts):
        self.mylog = mylog
        self.groups = groups
        self.hosts = cfghosts

    def get_host_name(self, hostsnames):
        # hostsnames 可以是列表，可以是ALL，可以是具体主机名
        # 还可以是组名
        rt_hostnames = []
        err_rt_hostnames = []
        if isinstance(hostsnames, list):
            # hosts.yaml 中部分主机 或 groups.yaml中指定的组
            for host in hostsnames:
                tmp_err_hosts = []
                if host in self.groups:
                    # host 是组，需要获取组员
                    if isinstance(self.groups[host], dict):
                        # 嵌套组
                        if "children" not in self.groups[host]:
                            self.mylog.cri("嵌套组配置错误，必须有children关键字")
                            raise Exception("嵌套组配置错误，必须有children关键字")
                        for children_group in self.groups[host]["children"]:
                            # 具体组名下面的hostname 支持正则表达式
                            for pattern in self.groups[children_group]:
                                ok_hostnames, err_hostnames = self.get_host_name_from_pattern(pattern)
                                rt_hostnames = rt_hostnames + ok_hostnames
                                tmp_err_hosts = tmp_err_hosts + err_hostnames
                    else:
                        # 非嵌套组， 具体组名下面的hostname 支持正则表达式
                        for pattern in self.groups[host]:
                            ok_hostnames, err_hostnames = self.get_host_name_from_pattern(pattern)
                            rt_hostnames = rt_hostnames + ok_hostnames
                            tmp_err_hosts = tmp_err_hosts + err_hostnames
                else:
                    # host 是具体的主机，支持正则表达式
                    ok_hostnames, err_hostnames = self.get_host_name_from_pattern(host)
                    rt_hostnames = rt_hostnames + ok_hostnames
                    tmp_err_hosts = tmp_err_hosts + err_hostnames
                if len(tmp_err_hosts) > 0:
                    err_rt_hostnames.append(host)

        elif isinstance(hostsnames, str):
            if hostsnames == "ALL":
                # hosts.yaml 中全部的主机
                for hostname in self.hosts["HOST"]:
                    rt_hostnames.append(hostname)
            else:
                raise Exception("action文件hosts配置有误，字符串类hosts只支持ALL,其他需要用[] 表示")
        else:
            raise Exception("action文件hosts配置有误，类型只能为ALL或[]")
        return rt_hostnames, err_rt_hostnames

    def get_host_name_from_pattern(self, pattern):
        # pattern 可以是正则表达式形式的
        # group.yaml 中组及action.yaml hosts 支持正则表达式，因此补仓改函数
        rt_hostnames = []
        err_hostnames = []
        m = PATTERN_WITH_SUBSCRIPT.match(pattern)

        # 不含[x:y]字符情况
        if not m:
            if pattern in self.hosts["HOST"]:
                rt_hostnames.append(pattern)
            else:
                err_hostnames.append(pattern)
        else:
            # 包含[x:y]字符情况
            (lable, start, sep, end) = m.groups()
            t_hosts = []
            for i in range(int(start), int(end) + 1):
                hostname = f"{lable}{str(i)}"
                if hostname in self.hosts["HOST"]:
                    rt_hostnames.append(hostname)

        if len(rt_hostnames) == 0:
            err_hostnames.append(pattern)
        return rt_hostnames, err_hostnames

    def check_hostname(self, hostsnames):
        # hostnames 为主机名列表，该函数检查主机名是否在hosts.yaml中
        rt_hostnames = []
        for hostname in hostsnames:
            if hostname not in self.hosts["HOST"]:
                # 检查失败，不在hosts.yaml中
                rt_hostnames.append(hostname)
        return rt_hostnames
