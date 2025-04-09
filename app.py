import os
import threading
import webbrowser
from flask import Flask, render_template, request, session, jsonify

from Tansible import Tansible
from lib.constants import DEFAULT_HOSTS_FILE, DEFAULT_ACTION_FILE, DEFAULT_GROUPS_FILE

app = Flask(__name__)
app.secret_key = 'your_secret_key'


def args_check(action_file, hosts_config_file, groups_config_file, workers, run_step_by_step=False):
    error_messages = {
        'action_file': '',
        'hosts_config_file': '',
        'groups_config_file': '',
        'workers': ''
    }
    if not os.path.exists(action_file):
        error_messages['action_file'] = f"action file {action_file} not exist"
    if not os.path.exists(hosts_config_file):
        error_messages['hosts_config_file'] = f"hosts file {hosts_config_file} not exist"
    if groups_config_file != DEFAULT_GROUPS_FILE and not os.path.exists(groups_config_file):
        error_messages['groups_config_file'] = f"groups file {groups_config_file} not exist"
    if run_step_by_step and workers > 1:
        error_messages['workers'] = "-s option only can be used in single thread mode"
    return error_messages


def get_directory_tree(path):
    tree = []
    for item in os.listdir(path):
        item_path = os.path.join(path, item)
        if os.path.isdir(item_path):
            subtree = {
                'name': item,
                'type': 'directory',
                'children': get_directory_tree(item_path)
            }
            tree.append(subtree)
        else:
            tree.append({
                'name': item,
                'type': 'file'
            })
    return tree


@app.route('/get_config_tree', methods=['GET'])
def get_config_tree():
    config_path = '.'  # 假设 config 目录在项目根目录下
    tree = get_directory_tree(config_path)
    return jsonify(tree)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        host_file_path = request.form.get('host_file_path', DEFAULT_HOSTS_FILE)
        group_file_path = request.form.get('group_file_path', DEFAULT_GROUPS_FILE)
        action_file_path = request.form.get('action_file_path', DEFAULT_ACTION_FILE)
        max_workers = request.form.get('max_workers')

        session['host_file_path'] = host_file_path
        session['group_file_path'] = group_file_path
        session['action_file_path'] = action_file_path
        session['max_workers'] = max_workers

        try:
            max_workers = int(max_workers) if max_workers else 1
            error_messages = args_check(action_file_path, host_file_path, group_file_path, max_workers)
            if any(error_messages.values()):
                session['error_messages'] = error_messages
                template_data = {
                    'default_hosts_file': DEFAULT_HOSTS_FILE,
                    'default_action_file': DEFAULT_ACTION_FILE,
                    'default_groups_file': DEFAULT_GROUPS_FILE,
                    'host_file_path': host_file_path,
                    'group_file_path': group_file_path,
                    'action_file_path': action_file_path,
                    'max_workers': max_workers,
                    'error_messages': error_messages
                }
                return render_template('index.html', **template_data)
        except ValueError as e:
            error_message = str(e)
            session['error_messages'] = {'workers': error_message}
            template_data = {
                'default_hosts_file': DEFAULT_HOSTS_FILE,
                'default_action_file': DEFAULT_ACTION_FILE,
                'default_groups_file': DEFAULT_GROUPS_FILE,
                'host_file_path': host_file_path,
                'group_file_path': group_file_path,
                'action_file_path': action_file_path,
                'max_workers': max_workers,
                'error_messages': session['error_messages']
            }
            return render_template('index.html', **template_data)

        if host_file_path and group_file_path and action_file_path:
            try:
                tansible = Tansible(
                    actions_file=action_file_path,
                    hosts_file=host_file_path,
                    groups_file=group_file_path,
                    max_workers=max_workers
                )
                tansible.action_func()
                result = tansible.result
                # 传递参数到结果页面
                return render_template('result.html', result=result,
                                       host_file_path=host_file_path,
                                       group_file_path=group_file_path,
                                       action_file_path=action_file_path,
                                       max_workers=max_workers)
            except Exception as e:
                error_message = f"Tansible 任务执行失败，错误信息：{str(e)}"
                return render_template('result.html', error=error_message)
        else:
            error_message = "请输入所有必要的文件路径。"
            return render_template('result.html', error=error_message)

    host_file_path = session.get('host_file_path', DEFAULT_HOSTS_FILE)
    group_file_path = session.get('group_file_path', DEFAULT_GROUPS_FILE)
    action_file_path = session.get('action_file_path', DEFAULT_ACTION_FILE)
    max_workers = session.get('max_workers', 1)
    error_messages = session.pop('error_messages', {})

    template_data = {
        'default_hosts_file': DEFAULT_HOSTS_FILE,
        'default_action_file': DEFAULT_ACTION_FILE,
        'default_groups_file': DEFAULT_GROUPS_FILE,
        'host_file_path': host_file_path,
        'group_file_path': group_file_path,
        'action_file_path': action_file_path,
        'max_workers': max_workers,
        'error_messages': error_messages
    }
    return render_template('index.html', **template_data)


def open_browser(host, port):
    webbrowser.open_new(f'http://{host}:{port}/')


if __name__ == '__main__':
    host = '127.0.0.1'
    port = 5000
    threading.Timer(1, open_browser, [host, port]).start()
    app.run(host, port, debug=True)
