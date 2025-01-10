# 这是一个示例 Python 脚本。
import argparse
import codecs
import os

codecs.register(lambda name: codecs.lookup('utf-8') if name == 'idna' else None)

from Tansible import Tansible
import lib.constants as C

def args_fun():
    parser = argparse.ArgumentParser(description='Tansible command line tool')
    parser.add_argument('-a', '--action_file', type=str, default=C.DEFAULT_ACTION_FILE,
                        help='input the action file name,like action.yml')
    parser.add_argument('-ho', '--hosts_config_file', type=str, default=C.DEFAULT_HOSTS_FILE,
                        help='input hosts file name,default is  hosts.yml')
    parser.add_argument('-g', '--groups_config_file', type=str, default=C.DEFAULT_GROUPS_FILE,
                        help='input groups file name,default is  groups.yml')
    parser.add_argument('-s', '--run_step_by_step', action='store_const', const=True,
                        help='enable step by step mode, only run with single thread and only for debug')
    parser.add_argument('-w', '--workers', type=int, default=1,
                        help='run with multi thread,you can set the number of threads here or in the action file')
    args = parser.parse_args()
    return args

# 参数判断
def args_check(args):
    if not os.path.exists(args.action_file):
        print(f"action file {args.action_file} not exist")
        exit(1)
    if not os.path.exists(args.hosts_config_file):
        print(f"hosts file {args.hosts_config_file} not exist")
        exit(1)
    # groups文件如果配置为非默认值，则必须存在，否则报错
    if args.groups_config_file != C.DEFAULT_GROUPS_FILE and not os.path.exists(args.groups_config_file):
        print(f"groups file {args.groups_config_file} not exist")
        exit(1)
    # -s 选项只能在单线程模式下使用
    if args.run_step_by_step and args.workers > 1 :
        print("-s option only can be used in single thread mode")
        exit(1)

def work():
    args = args_fun()
    print(args)
    args_check(args)
    obj = Tansible(actions_file=args.action_file, hosts_file=args.hosts_config_file,
                   groups_file=args.groups_config_file, max_workers=args.workers, step_by_step=args.run_step_by_step)
    obj.action_func()


if __name__ == '__main__':
    work()
