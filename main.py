# -*- coding: utf-8 -*-
from Tansible import Tansible
import sys
import os


def myfunc():
    obj = Tansible()
    a, b = obj.check_acton_hostcfg()
    if not a:
        print(b)
    else:
        print("hosts 检查通过")


def main():
    choise = input("是否运行，借机调整窗口大小吧（y/n）：")
    if choise not in ["y", "n"]:
        print("输入错误")
    if choise == "n":
        print("选择退出...")
    if choise == "y":
        if len(sys.argv) == 2:
            root_dir = os.path.abspath('.')
            configpath = os.path.join(root_dir, "config", sys.argv[1])
            obj = Tansible(configpath)
            obj.action_func()
        else:
            obj = Tansible()
            obj.action_func()


if __name__ == '__main__':
    main()
    # myfunc()

