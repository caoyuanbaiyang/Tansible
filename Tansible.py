import importlib
import os.path
import threading
import time
import webbrowser

import lib.constants as C
import lib.hosts as host_func
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures
import lib.paramiko_ssh as paramiko_ssh
from lib.readcfg import ReadCfg


class Tansible(object):
    def __init__(self, actions_file=None, hosts_file=None, groups_file=None, max_workers=None, step_by_step=None):
        if groups_file == "config/groups.yaml":
            self.groups = ReadCfg().readcfg(groups_file) if os.path.exists(groups_file) else []
        else:
            self.groups = ReadCfg().readcfg(groups_file)
        self.hosts = ReadCfg().readcfg(hosts_file) if hosts_file else []
        self.actions, self.actions_file_name = C.load_actions_file(actions_file)

        self.max_workers = max_workers if max_workers is not None else self.actions["PUBLIC"].get("max_workers", 1)

        self.step_by_step = step_by_step if step_by_step is not None else False

        self.result = []

    def for_init(self):
        # 初始化函数
        pass

    def __action_func_inner(self, taskname, hostname, modelname, param):
        try:
            start_time = time.time()
            C.log.info(f"------模块:{modelname},主机:{hostname}")
            C.log.debug(f"Thread ID: {threading.get_ident()}")
            host = self.hosts["HOST"][hostname]
            C.PackHost(self.hosts["PUBLIC"], host)
            conn_timeout = host.get("conn_timeout")
            # 利用paramiko_ssh 连接主机
            conn = None
            if host["connect_type"] == 1:
                # 密码连接
                conn = paramiko_ssh.Connection(host=host["ip"], user=host["username"], conn_type=host["connect_type"],
                                               password=host["password"],timeout=conn_timeout).connect()
            if host["connect_type"] == 2:
                #  密钥连接
                conn = paramiko_ssh.Connection(host=host["ip"], user=host["username"], conn_type=host["connect_type"],
                                               key_filename=host["key_filename"],
                                               passphrase=host["passphrase"],timeout=conn_timeout).connect()
            # 模块翻译,如果在翻译列表中则用翻译后的重新赋值
            if modelname in C.MODULE_TRANS_DICT:
                modelname = C.MODULE_TRANS_DICT[modelname]

            m = importlib.import_module("model." + modelname + "." + modelname)
            result = m.ModelClass(C.log, conn, hostname, param, host).action()

            end_time = time.time()

            # 补充模块信息和主机信息
            result["taskname"] = taskname
            result["hostname"] = hostname
            result["modelname"] = modelname
            result["costtime"] = end_time - start_time

        except Exception as e:
            end_time = time.time()
            costtime = end_time - start_time
            C.log.cri(f"执行失败: 错误信息-{e}")
            result = {"status": "failed", "msg": f"执行失败-{e}", "taskname": taskname, "hostname": hostname, "modelname": modelname, "costtime": costtime}
        finally:
            return result

    def run_multi_thread(self, hosts_obj):
        C.log.debug("多线程执行")
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
                    taskname = ""
                    for modelname, param in task.items():
                        if modelname == "name":
                            taskname= task["name"]
                            C.log.info(f'*********执行任务：{taskname}*********')
                            continue
                        if modelname == "GetHostList":
                            C.log.info(f"主机列表：{hostname_list}")
                            continue
                        if modelname == "BreakPoint":
                            # 等待所有线程完成
                            C.log.info("等待所有线程执行完成...")
                            concurrent.futures.wait(futures)
                            C.log.info("所有线程执行完成")
                            continue
                        # 每个模块都要对所有设置的主机去执行，因此此处遍历所有主机去调用模块动作
                        for hostname in hostname_list:
                            futures.append(t.submit(self.__action_func_inner, taskname, hostname, modelname, param))
        for future in futures:
            self.result.append(future.result(timeout=120))

    def run_single_thread(self, hosts_obj):
        C.log.debug("单线程执行")
        # 每个action 就是 - hosts: 开头的部分内容，这就是每个action的配置
        for action in self.actions["ACTION"]:
            # 根据hosts:ALL 配置获取所有主机名的列表
            hostname_list, _ = hosts_obj.get_host_name(action["hosts"])
            # 遍历task列表，每个task 开头 - 模块名称 或者 - name:任务说明
            for task in action["tasks"]:
                # 按调用的模块依次执行
                taskname = ""
                for modelname, param in task.items():
                    if modelname == "name":
                        taskname = task["name"]
                        C.log.info(f'*********执行任务：{taskname}*********')
                        continue
                    if modelname == "GetHostList":
                        C.log.info(f"主机列表：{hostname_list}")
                        continue
                    if modelname == "BreakPoint":
                        # 单线程运行模式下，支持断点模块，该模块下，每个主机都会暂停
                        C.breakpoint_choice(param['name'])
                        continue
                    # 每个模块都要对所有设置的主机去执行，因此此处遍历所有主机去调用模块动作
                    for hostname in hostname_list:
                        run_result = self.__action_func_inner(taskname, hostname, modelname, param)
                        # 将主机、模块运行的结果run_result 存入self.result中
                        self.result.append(run_result)
                        if self.step_by_step:
                            self.step_by_step = C.step_by_step_choice()

    def action_func(self):
        start_time = time.time()
        # 检查hosts 配置是否有错误的，如果有错误，则不运行
        hosts_obj = host_func.hosts(C.log, self.groups, self.hosts)
        check, err_list = host_func.check_action_hostcfg(self.actions, hosts_obj)

        if not check:
            C.log.cri(f"action 配置文件中hosts配置错误，hosts.yaml无相关配置：{err_list}")
            raise Exception("action 配置文件hosts配置错误")


        C.log.green(f'############开始任务{self.actions_file_name}############')
        if self.max_workers > 1:
            self.run_multi_thread(hosts_obj)
        else:
            self.run_single_thread(hosts_obj)

        # 执行完毕后，对执行结果进行统计
        self.statistics_result()
        end_time = time.time()
        C.log.info('')
        C.log.info(f"time cost:{end_time - start_time:.2f} seconds")
        C.log.green(f'############任务{self.actions_file_name}执行完成############')
        # self.dump_result_file()
        # self.dump_result_to_html()

    def statistics_result(self):
        # 统计执行结果
        success_count = 0
        failed_count = 0
        for result in self.result:
            if result['status'] == 'success':
                success_count += 1
            else:
                failed_count += 1
        C.log.info('')
        C.log.info('PLAY RECAP******************************************************************************')
        # 打印执行结果详细信息
        C.log.info('')
        status, taskname, modelname, hostname, costtime = "执行结果", "任务", "模块名", "主机名", "执行秒数"
        C.log.info(f'{status:15s}{taskname:25s}{modelname:25s}{hostname:25s}{costtime}')
        for k in self.result:
            if k['status'] == 'success':
                C.log.green(f"{k['status']:15s}{k['taskname']:25s}{k['modelname']:25s}{k['hostname']:25s}{k['costtime']:.0f}")
            else:
                C.log.info(f"{k['status']:15s}{k['taskname']:25s}{k['modelname']:25s}{k['hostname']:25s}{k['costtime']:.0f}")

        if success_count > 0:
            C.log.green(f'成功执行{success_count}个任务')
        if failed_count > 0:
            C.log.error(f'失败执行{failed_count}个任务')
            
    def dump_result_file(self):
        # 将执行结果写入到结果文件
        result_file = C.DEFAULT_LOG_DIR + "tansible"+C.formatted_time+".result.log"
        C.log.debug("self.result长度：" + str(len(self.result)))
        with open(result_file, mode='w',encoding="utf-8",errors='ignore') as f:
            status,taskname, modelname, hostname, costtime, msg = "执行结果", "任务", "模块名", "主机名", "执行秒数", "返回结果"
            f.write(f'{status:15s}{taskname:25s}{modelname:25s}{hostname:25s}{costtime}    {msg}\n')
            for result in self.result:
                content = f"{result['status']:15s}{result['taskname']:25s}{result['modelname']:25s}{result['hostname']:25s}{result['costtime']:5.0f}    {result['msg']}"
                if not content.endswith("\n"):
                    content = content + "\n"
                f.write(content)

    # 将执行结果导出为 HTML 文件
    def dump_result_to_html(self, host_file_path, group_file_path, action_file_path, max_workers, show=True):
        # 将执行结果写入到结果文件
        result_file = C.DEFAULT_LOG_DIR + "tansible" + C.formatted_time + ".result.html"
        C.log.debug("self.result长度：" + str(len(self.result)))

        # 读取模板文件
        with open('template.html', 'r', encoding='utf-8') as template_file:
            template = template_file.read()

        table_rows = ""
        for result in self.result:
            # 将换行符替换为 HTML 换行标签
            msg_with_br = result['msg'].replace('\n', '<br>')
            row_class = "failed-row" if result['status'] == 'failed' else ""
            table_rows += f"""
                <tr class="{row_class}">
                    <td style="white-space: nowrap">{result['status']}</td>
                    <td style="white-space: nowrap">{result['taskname']}</td>
                    <td style="white-space: nowrap">{result['modelname']}</td>
                    <td style="white-space: nowrap">{result['hostname']}</td>
                    <td style="white-space: nowrap">{result['costtime']:.0f}</td>
                    <td style="white-space: normal">{msg_with_br}</td>
                </tr>
            """

        # 渲染模板
        html_content = template.replace('{{table_rows}}', table_rows)
        html_content = html_content.replace('{{host_file_path}}', host_file_path)
        html_content = html_content.replace('{{group_file_path}}', group_file_path)
        html_content = html_content.replace('{{action_file_path}}', action_file_path)
        html_content = html_content.replace('{{max_workers}}', str(max_workers))

        # 写入 HTML 文件
        with open(result_file, mode='w', encoding="utf-8", errors='ignore') as f:
            f.write(html_content)

        C.log.info(f"执行结果已导出到 {result_file}")

        # 打开 HTML 文件
        if show:
            try:
                file_url = 'file://' + os.path.abspath(result_file)
                webbrowser.open(file_url)
            except Exception as e:
                C.log.error(f"无法在浏览器中打开 {result_file}: {e}")