# -*- coding: utf-8 -*-

import json
import os
import re
import time

import chardet
import paramiko


def ssh_reply(chanel_recv):
    whcode = chardet.detect(chanel_recv)['encoding']
    reply = chanel_recv.decode(whcode, 'ignore')
    return reply


def execute(cmd, stdin, stdout):
    """
    :param stdout:
    :param stdin:
    :param cmd: the command to be executed on the remote computer
    :examples:  execute('ls')
                execute('finger')
                execute('cd folder_name')
    """
    cmd = cmd.strip('\n')
    stdin.write(cmd + '\n')
    finish = 'end of stdOUT buffer. finished with exit status'
    echo_cmd = 'echo {} $?'.format(finish)
    stdin.write(echo_cmd + '\n')
    shin = stdin
    stdin.flush()

    shout = []
    sherr = []
    exit_status = 0

    for line_b in stdout:
        if not chardet.detect(line_b)['encoding']:
            __encoding = 'UTF-8'
        else:
            __encoding = chardet.detect(line_b)['encoding']
        line = line_b.decode(__encoding, 'ignore')

        if str(line).startswith(cmd) or str(line).startswith(echo_cmd):
            # up for now filled with shell junk from stdin
            shout = []
        elif str(line).startswith(finish):
            # our finish command ends with the exit status
            exit_status = int(str(line).rsplit(maxsplit=1)[1])
            if exit_status:
                # stderr is combined with stdout.
                # thus, swap sherr with shout in a case of failure.
                sherr = shout
                shout = []
            break
        else:
            # get rid of 'coloring and formatting' special characters
            shout.append(re.compile(r'(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]').sub('', line).
                         replace('\b', '').replace('\r', ''))

    # first and last lines of shout/sherr contain a prompt
    if shout and echo_cmd in shout[-1]:
        shout.pop()
    if shout and cmd in shout[0]:
        shout.pop(0)
    if sherr and echo_cmd in sherr[-1]:
        sherr.pop()
    if sherr and cmd in sherr[0]:
        sherr.pop(0)

    return shin, shout, sherr


class ModelClass(object):
    def __init__(self, mylog):
        self.mylog = mylog

    def __execcommand1(self, ssh, command, timeout=5):
        try:
            chanel = ssh.invoke_shell()
            chanel.send("export LANG=en_US.UTF-8 \n")
            time.sleep(0.01)
            chanel.send(command + "\n")
            time.sleep(0.1)

            buff = ""
            i = 0
            while not buff.endswith("$ "):
                resp = chanel.recv(9999)
                time.sleep(0.1)
                reply = ssh_reply(resp)
                buff = reply
                i = i + 1
                while i > 50:
                    break

        except paramiko.ssh_exception.SSHException:
            self.mylog.info("命令执行失败:" + command)
            return [False, "命令执行失败:" + command]
        except Exception as e:
            self.mylog.info(e)
            self.mylog.info("命令执行失败:" + command)
            return [False, e]

        self.mylog.info(buff)
        return [True, buff]

    def __execcommand(self, ssh, command, timeout=5):
        try:
            channel = ssh.invoke_shell()
            stdin = channel.makefile('wb')
            stdout = channel.makefile('rb')
            channel.send("export LANG=en_US.UTF-8 \n")

            sin, sout, serr = execute(command, stdin, stdout)

        except paramiko.ssh_exception.SSHException:
            self.mylog.info("命令执行失败:" + command)
            return [False, "命令执行失败:" + command]
        except Exception as e:
            self.mylog.info(e)
            self.mylog.info("命令执行失败:" + command)
            return [False, e]

        for m in sout:
            self.mylog.info("out:")
            self.mylog.info(m.replace("\n", ""))
        for m in serr:
            self.mylog.info("err:")
            self.mylog.info(m.replace("\n", ""))

        return [True, sout]

    def action(self, ssh, hostname, param, hostparam=None):
        if hostparam is None:
            hostparam = []
        for cfg_key, cfg_value in param.items():
            if cfg_key not in ["cmd"]:
                raise Exception('配置文件配置错误:未知参数:{param}'.format(param=json.dumps(param)))
        self.__execcommand(ssh, param["cmd"])
