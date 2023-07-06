# -*- coding: utf-8 -*-
from Tansible_single_thread import Tansible
import sys
import os
import argparse


def myfunc():
    obj = Tansible()
    a, b = obj.check_acton_hostcfg()
    if not a:
        print(b)
    else:
        print("hosts 检查通过")


def work():
    parser = argparse.ArgumentParser(description='Process a file and enable single-step mode.')
    parser.add_argument('filename', metavar='FILE', help='input file name')
    parser.add_argument('-s', '--single-step', action='store_true', help='enable single-step mode')

    args = parser.parse_args()

    configpath = os.path.join("config", sys.argv[1])
    obj = Tansible(configpath)
    if args.single_step:
        obj.action_func(single_step=True)
    else:
        obj.action_func(single_step=False)


def main():
    if len(sys.argv) == 2:
        configpath = os.path.join("config", sys.argv[1])
        obj = Tansible(configpath)
        obj.action_func()
    else:
        obj = Tansible()
        obj.action_func()


if __name__ == '__main__':
    work()
    # myfunc()
