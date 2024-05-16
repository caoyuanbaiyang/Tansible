import importlib
import sys
import threading
import time

import lib.constants as C
import lib.hosts as host_func
from concurrent.futures import ThreadPoolExecutor
import lib.paramiko_ssh as paramiko_ssh


class Tansible(object):
    def __init__(self, actions_file=None, hosts_file=None, groups_file=None, max_workers=None, step_by_step=None):
        self.groups = C.load_groups_file(groups_file) if groups_file else []
        self.hosts = C.load_hosts_file(hosts_file) if hosts_file else []
        self.actions, self.actions_file_name = C.load_actions_file(actions_file)

        if max_workers is not None:
            self.max_workers = max_workers
        else:
            if "max_workers" in self.actions["PUBLIC"]:
                self.max_workers = self.actions["PUBLIC"]["max_workers"]
            else:
                self.max_workers = 1

        if step_by_step is not None:
            self.step_by_step = step_by_step
        else:
            self.step_by_step = False

        self.result = []

    def for_init(self):
        # 初始化函数
        pass

    def __action_func_inner(self, hostname, modelname, param):
        try:
            C.logger.info(f"------模块:{modelname},主机:{hostname}")
            C.logger.debug(f"Thread ID: {threading.get_ident()}")
            host = self.hosts["HOST"][hostname]
            C.PackHost(self.hosts["PUBLIC"], host)

            # 利用paramiko_ssh 连接主机
            conn = None
            if host["connect_type"] == 1:
                # 密码连接
                conn = paramiko_ssh.Connection(host=host["ip"], user=host["username"], conn_type=host["connect_type"],
                                               password=host["password"]).connect()
            if host["connect_type"] == 2:
                #  密钥连接
                conn = paramiko_ssh.Connection(host=host["ip"], user=host["username"], conn_type=host["connect_type"],
                                               key_filename=host["key_filename"],
                                               passphrase=host["passphrase"]).connect()

            m = importlib.import_module("model." + modelname + "." + modelname)
            result = m.ModelClass(C.logger, conn, hostname, param, host).action()
            # 补充模块信息和主机信息
            result["hostname"] = hostname
            result["modelname"] = modelname

        except Exception as e:
            C.logger.cri(f"执行失败: 错误信息-{e}")
            result = {"status": "failed", "msg": "执行失败", "hostname": hostname, "modelname": modelname}
        finally:
            return result

    def run_multi_thread(self, hosts_obj):
        C.logger.debug("多线程执行")
        futures = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as t:
            # 根据action 配置文件的顺序开始执行，引入多线程方式
            # 每个action 就是 - hosts: 开头的部分内容，这就是每个action的配置
            for action in self.actions["ACTION"]:
                # 根据hosts:ALL 配置获取所有主机名的列表
                hostname_list, _ = hosts_obj.get_host_name(action["hosts"])
                # 遍历task列表，每个task 开头 - 模块名称 或者 - name:任务说明
                for task in action["tasks"]:
                    # 按调用的模块依次执行
                    for modelname, param in task.items():
                        if modelname == "name":
                            C.logger.info(f'*********执行任务：{task["name"]}*********')
                            continue
                        if modelname == "GetHostList":
                            C.logger.info(f"主机列表：{hostname_list}")
                            continue
                        if modelname == "BreakPoint":
                            C.logger.info(f"并发模式下不支持BreakPoint模块")
                            continue
                        # 每个模块都要对所有设置的主机去执行，因此此处遍历所有主机去调用模块动作
                        for hostname in hostname_list:
                            futures.append(t.submit(self.__action_func_inner, hostname, modelname, param))
        for future in futures:
            self.result.append(future.result())
            C.logger.debug(future.result())

    def run_single_thread(self, hosts_obj):
        C.logger.debug("单线程执行")
        # 每个action 就是 - hosts: 开头的部分内容，这就是每个action的配置
        for action in self.actions["ACTION"]:
            # 根据hosts:ALL 配置获取所有主机名的列表
            hostname_list, _ = hosts_obj.get_host_name(action["hosts"])
            # 遍历task列表，每个task 开头 - 模块名称 或者 - name:任务说明
            for task in action["tasks"]:
                # 按调用的模块依次执行
                for modelname, param in task.items():
                    if modelname == "name":
                        C.logger.info(f'*********执行任务：{task["name"]}*********')
                        continue
                    if modelname == "GetHostList":
                        C.logger.info(f"主机列表：{hostname_list}")
                        continue
                    if modelname == "Breakpoint":
                        # 单线程运行模式下，支持断点模块，该模块下，每个主机都会暂停
                        C.breakpoint_choice(param['name'])
                        continue
                    # 每个模块都要对所有设置的主机去执行，因此此处遍历所有主机去调用模块动作
                    for hostname in hostname_list:
                        run_result = self.__action_func_inner(hostname, modelname, param)
                        # 将主机、模块运行的结果run_result 存入self.result中
                        self.result.append(run_result)
                        C.logger.debug(run_result)
                        if self.step_by_step:
                            self.step_by_step = C.step_by_step_choice()

    def action_func(self):
        start_time = time.time()
        # 检查hosts 配置是否有错误的，如果有错误，则不运行
        hosts_obj = host_func.hosts(C.logger, self.groups, self.hosts)
        check, err_list = host_func.check_action_hostcfg(self.actions, hosts_obj)

        if not check:
            C.logger.cri(f"action 配置文件中hosts配置错误，hosts.yaml无相关配置：{err_list}")
            raise Exception("action 配置文件hosts配置错误")

        C.adjust_window_size()

        C.logger.green(f'############开始任务{self.actions_file_name}############')
        if self.max_workers > 1:
            self.run_multi_thread(hosts_obj)
        else:
            self.run_single_thread(hosts_obj)

        # 执行完毕后，对执行结果进行统计
        self.statistics_result()
        end_time = time.time()
        C.logger.info('')
        C.logger.info(f"time cost:{end_time - start_time:.2f} seconds")
        C.logger.green(f'############任务{self.actions_file_name}执行完成############')

    def statistics_result(self):
        # 统计执行结果
        success_count = 0
        failed_count = 0
        for result in self.result:
            if result['status'] == 'success':
                success_count += 1
            else:
                failed_count += 1
        C.logger.info('')
        C.logger.info('PLAY RECAP******************************************************************************')
        if success_count > 0:
            C.logger.green(f'成功执行{success_count}个任务')
        if failed_count > 0:
            C.logger.error(f'失败执行{failed_count}个任务')

        # 打印执行结果详细信息
        C.logger.info('')
        status, modelname, hostname = "执行结果",  "模块名", "主机名"
        C.logger.info(f'{status:15s}{modelname:25s}{hostname:25s}')
        for k in self.result:
            if k['status'] == 'success':
                C.logger.green(f"{k['status']:15s}{k['modelname']:25s}{k['hostname']:25s}")
            else:
                C.logger.info(f"{k['status']:15s}{k['modelname']:25s}{k['hostname']:25s}")
