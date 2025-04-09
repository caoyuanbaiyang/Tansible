import os
import threading
import webbrowser

from flask import Flask, render_template, request, session
from Tansible import Tansible
from lib.constants import DEFAULT_HOSTS_FILE, DEFAULT_ACTION_FILE, DEFAULT_GROUPS_FILE

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 设置密钥，用于加密会话数据

def args_check(action_file, hosts_config_file, groups_config_file, workers, run_step_by_step=False):
    error_messages = []
    if not os.path.exists(action_file):
        error_messages.append(f"action file {action_file} not exist")
    if not os.path.exists(hosts_config_file):
        error_messages.append(f"hosts file {hosts_config_file} not exist")
    # groups文件如果配置为非默认值，则必须存在，否则报错
    if groups_config_file != DEFAULT_GROUPS_FILE and not os.path.exists(groups_config_file):
        error_messages.append(f"groups file {groups_config_file} not exist")
    # -s 选项只能在单线程模式下使用
    if run_step_by_step and workers > 1 :
        error_messages.append("-s option only can be used in single thread mode")
    return error_messages

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # 获取输入的文件路径
        host_file_path = request.form.get('host_file_path', DEFAULT_HOSTS_FILE)
        group_file_path = request.form.get('group_file_path', DEFAULT_GROUPS_FILE)
        action_file_path = request.form.get('action_file_path', DEFAULT_ACTION_FILE)
        # 获取并发线程数
        max_workers = request.form.get('max_workers')

        # 将输入信息存储到会话中
        session['host_file_path'] = host_file_path
        session['group_file_path'] = group_file_path
        session['action_file_path'] = action_file_path
        session['max_workers'] = max_workers

        # 校验输入的值
        try:
            max_workers = int(max_workers) if max_workers else 1
            error_messages = args_check(action_file_path, host_file_path, group_file_path, max_workers)
            if error_messages:
                error_message = ", ".join(error_messages)
                return render_template('result.html', error=error_message, host_file_path=host_file_path,
                                       group_file_path=group_file_path, action_file_path=action_file_path,
                                       max_workers=max_workers)
        except ValueError as e:
            error_message = str(e)
            return render_template('result.html', error=error_message, host_file_path=host_file_path,
                                   group_file_path=group_file_path, action_file_path=action_file_path,
                                   max_workers=max_workers)

        if host_file_path and group_file_path and action_file_path:
            try:
                tansible = Tansible(
                    actions_file=action_file_path,
                    hosts_file=host_file_path,
                    groups_file=group_file_path,
                    max_workers=max_workers
                )
                # 模拟执行任务
                tansible.action_func()
                result = tansible.result
                return render_template('result.html', result=result, host_file_path=host_file_path,
                                       group_file_path=group_file_path, action_file_path=action_file_path,
                                       max_workers=max_workers)
            except Exception as e:
                error_message = f"Tansible 任务执行失败，错误信息：{str(e)}"
                return render_template('result.html', error=error_message, host_file_path=host_file_path,
                                       group_file_path=group_file_path, action_file_path=action_file_path,
                                       max_workers=max_workers)
        else:
            error_message = "请输入所有必要的文件路径。"
            return render_template('result.html', error=error_message, host_file_path=host_file_path,
                                   group_file_path=group_file_path, action_file_path=action_file_path,
                                   max_workers=max_workers)

    # 从会话中获取之前输入的信息，如果没有则使用默认值
    host_file_path = session.get('host_file_path', DEFAULT_HOSTS_FILE)
    group_file_path = session.get('group_file_path', DEFAULT_GROUPS_FILE)
    action_file_path = session.get('action_file_path', DEFAULT_ACTION_FILE)
    max_workers = session.get('max_workers')

    return render_template('index.html', default_hosts_file=DEFAULT_HOSTS_FILE, default_action_file=DEFAULT_ACTION_FILE,
                           default_groups_file=DEFAULT_GROUPS_FILE, host_file_path=host_file_path,
                           group_file_path=group_file_path, action_file_path=action_file_path, max_workers=max_workers)

def open_browser(host, port):
    webbrowser.open_new(f'http://{host}:{port}/')

if __name__ == '__main__':
    host = '127.0.0.1'
    port = 5000
    threading.Timer(1, open_browser, [host, port]).start()
    app.run(host, port, debug=True)