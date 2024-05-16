# 这是一个示例 Python 脚本。
import argparse


from Tansible import Tansible


def args_fun():
    parser = argparse.ArgumentParser(description='Tansible command line tool')
    parser.add_argument('-a', '--action_file', type=str, default='config/action.yaml',
                        help='input the action file name,like action.yml')
    parser.add_argument('-ho ', '--hosts_config_file', type=str, default='config/hosts.yaml',
                        help='input hosts file name,default is  hosts.yml')
    parser.add_argument('-g ', '--groups_config_file', type=str, default='config/groups.yaml',
                        help='input groups file name,default is  groups.yml')
    parser.add_argument('-s ', '--run_step_by_step', action='store_const', const=True,
                        help='enable step by step mode, only run with single thread and only for debug')
    parser.add_argument('-w ', '--workers', type=int,
                        help='run with multi thread,you can set the number of threads here or in the action file')
    args = parser.parse_args()
    return args


def work():
    print(
        "usage: Tansible.exe [-h] [-a playbook] [-ho hosts_config_file] [-g groups_config_files] [-s] [-w workers]...")
    args = args_fun()
    print(args)
    obj = Tansible(actions_file=args.action_file, hosts_file=args.hosts_config_file,
                   groups_file=args.groups_config_file, max_workers=args.workers, step_by_step=args.run_step_by_step)
    obj.action_func()


if __name__ == '__main__':
    work()
