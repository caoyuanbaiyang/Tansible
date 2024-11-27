# (c) 2012, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.


import os
import pipes
import re
import stat
import time
from pathlib import Path

import chardet
import select
from Tools.scripts.md5sum import bufsize

import lib.constants as C

# prevent paramiko warning noise -- see http://stackoverflow.com/questions/3920502/
import paramiko

# keep connection objects on a per host basis to avoid repeated attempts to reconnect

SSH_CONNECTION_CACHE = {}
SFTP_CONNECTION_CACHE = {}


class Connection(object):
    """ SSH based connections with Paramiko """

    def __init__(self, host, user, conn_type, password=None, key_filename=None, passphrase=None, port=22, timeout=3):

        self.ssh = None
        self.sftp = None
        self.host = host
        self.port = port
        self.user = user
        self.conn_type = conn_type
        self.password = password
        self.key_filename = key_filename
        self.timeout = timeout
        self.passphrase = passphrase

        if self.conn_type == '1':
            # password
            self.key_filename = None
        if self.conn_type == '2':
            # key_file
            self.password = None

    def _cache_key(self):
        return "%s__%s__" % (self.host, self.user)

    def connect(self):
        cache_key = self._cache_key()
        if cache_key in SSH_CONNECTION_CACHE:
            self.ssh = SSH_CONNECTION_CACHE[cache_key]
        else:
            self.ssh = SSH_CONNECTION_CACHE[cache_key] = self._connect_uncached()
        return self

    def _connect_uncached(self):
        """ activates the connection object """

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        allow_agent = True
        if self.conn_type == '1':
            # password
            allow_agent = False
        try:
            ssh.connect(self.host, username=self.user, allow_agent=allow_agent, look_for_keys=True,
                        key_filename=self.key_filename, password=self.password,
                        timeout=self.timeout, port=self.port, passphrase=self.passphrase)
        except Exception as e:
            msg = str(e)
            if "PID check failed" in msg:
                raise Exception(
                    "paramiko version issue, please upgrade paramiko on the machine running ansible")
            elif "Private key file is encrypted" in msg:
                msg = 'ssh %s@%s:%s : %s\nTo connect as a different user, use -u <username>.' % (
                    self.user, self.host, self.port, msg)
                raise Exception(msg)
            else:
                raise Exception(msg)

        return ssh

    def exec_command(self, cmd, executable='/bin/sh', exec_timeout=C.DEFAULT_COMMAND_EXEC_TIMEOUT):
        """ run a command on the remote host """

        bufsize = 4096
        timeout = 10
        try:
            chan = self.ssh.get_transport().open_session()
        except Exception as e:
            msg = "Failed to open session"
            if len(str(e)) > 0:
                msg += ": %s" % str(e)
            raise Exception(msg)

        if executable:
            quoted_command = executable + ' -c ' + pipes.quote(cmd)
        else:
            quoted_command = cmd
        C.log.debug(f"EXEC {quoted_command} at {self.host}")
        chan.exec_command(quoted_command)

        stdout = []
        stderr = []

        start_time = time.time()
        # Read stdout
        _ready = chan.recv_ready()
        while not _ready:
            if time.time() - start_time > exec_timeout:
                exit_status = 1
                stderr = f'执行命令{cmd}超时{exec_timeout},执行时间{round(time.time() - start_time)}'
                return exit_status, '', ''.join(stdout), ''.join(stderr)
            _ready, _, _ = select.select([chan], [], [], timeout)
            time.sleep(0.1)
            print('select.select sleep 0.1')

        while chan.recv_ready():
            data = chan.recv(bufsize)
            stdout.append(data)
            print('chan.recv ')
            if not data:
                break

        # Read stderr
        while chan.recv_stderr_ready():
            data = chan.recv_stderr(bufsize)
            stderr.append(data)

        exit_status = chan.recv_exit_status()
        stdout = b''.join(stdout).decode('utf-8', 'ignore')
        stderr = b''.join(stderr).decode('utf-8', 'ignore')
        return exit_status, '', stdout, stderr

    def exec_command_invoke_shell(self, cmd, end_pattern=C.DEFAULT_SSH_END_PATTERN, chan_timeout=C.DEFAULT_CONNECT_TIMEOUT, exec_timeout=C.DEFAULT_COMMAND_EXEC_TIMEOUT):
        """ run a command on the remote host """
        '''
        :param cmd: command to be executed
        :param chan_timeout: timeout for the channel
        :param exec_timeout: timeout for the execution of the command
        '''
        bufsize = 65536
        chan = self.ssh.invoke_shell()
        chan.send(f'{cmd}  \n')
        chan.settimeout(chan_timeout)
        C.log.debug(message=f"EXEC {cmd} at {self.host}")
        # 读取输出直到命令完成
        stdout = ''
        start_time = time.time()

        while True:
            time.sleep(0.2)  # 短暂等待

            if time.time() - start_time > exec_timeout:
                exit_status = 1
                stderr = f'执行命令{cmd}超时{exec_timeout},执行时间{round(time.time() - start_time)}'
                return exit_status, '', stdout, stderr

            if chan.recv_ready():
                stdout += chan.recv(bufsize).decode('utf-8', errors='ignore')

            # 检查是否出现了提示符,如果出现了提示符，则认为命令执行完成，无须再循环获取了
            if re.search(end_pattern, stdout):  # 假设提示符为 $, # 或 >
                break

        chan.send(f'echo $? \n')
        exit_stdout = ''
        while True:
            time.sleep(0.2)  # 短暂等待

            if chan.recv_ready():
                exit_stdout += chan.recv(bufsize).decode('utf-8', errors='ignore')

            # 检查是否出现了提示符,如果出现了提示符，则认为命令执行完成，无须再循环获取了
            if re.search(end_pattern, stdout):  # 假设提示符为 $, # 或 >
                break
        exit_status = int(exit_stdout.strip().split('\n')[-2])
        return exit_status, '', stdout, stdout

    def exec_command_invoke_shell_1(self, cmd):
        """ run a command on the remote host """

        channel = self.ssh.invoke_shell()
        stdin = channel.makefile('wb')
        stdout = channel.makefile('rb')
        channel.send("export LANG=en_US.UTF-8 \n")
        C.log.debug(f"EXEC {cmd} at {self.host}")
        exit_status, _, stdout, stderr = execute(cmd, stdin, stdout)
        return exit_status, '', ''.join(stdout), ''.join(stderr)

    def exec_command_qk(self, command, result, end_flag=None, out_line_Num=3, timeout=10):
        """
        对于第一次登陆时的提示符行以及命令执行结束时的提示符行会被过滤，奕即提示符行尽量不要与结果置为同一行，记得脚本换行。
        :param ssh:
        :param command:
        :param end_flag:输出结束关键字，用于执行的脚本时间比较长，输出比较多时判断命令执行成功的标志。
        :param out_line_Num: return值中的out总行数，当一条命令返回行数多余out_line_Num时，将只保留后面的内容，丢弃前面的
        :return: 返回out
        """
        # out用于保存返回的输出，其他输出仅打印至日志中
        out = list()
        # 用于记录输出的索引，只需要保留最后3条
        out_index = 0
        # 用于删除第一次命令符提示符的标志
        first_line = True
        trans = self.ssh.get_transport()
        channel = trans.open_session(timeout=timeout)
        channel.get_pty()
        channel.settimeout(timeout)
        channel.invoke_shell()
        # 上一次剩余的数据，有可能不是完整一行
        rstlast = b''
        # 先要等待登录成功提示符
        while True:
            time.sleep(0.2)
            channel.recv_ready()
            rst1 = channel.recv(1024)
            rst1 = rstlast + rst1
            lines = rst1.split(b'\n')
            rstlast = lines[-1]
            if C.system_match(C.decode_line(rstlast)):
                break
        # 发送命令
        channel.send(command + '\n')
        # 等待下一个命令提示符结束，或者等待特定结束标识
        command_timeout = 0
        while True:
            time.sleep(0.2)
            command_timeout = command_timeout + 0.2
            if command_timeout > timeout:
                C.log.error(f'执行命令{command}超时{timeout}')
                raise Exception(f'执行命令{command}超时{timeout}')
            success = False
            channel.recv_ready()
            rst1 = channel.recv(1024)
            rst1 = rstlast + rst1
            lines = rst1.split(b'\n')
            if first_line and len(lines) > 1:
                first_line = False
                del lines[0]
            for line in lines[:-1]:
                line = C.decode_line(line)
                line = line.replace('\r', '')
                if line.strip() == "":
                    continue
                if not success:
                    if out_index < out_line_Num:
                        out.append(line)
                        out_index += 1
                    else:
                        out.append(line)
                        del out[0]
                if end_flag is None and C.system_match(line):
                    success = True
                if end_flag is not None and line.find(end_flag) != -1:
                    success = True

            # 无法判断lines[-1]这一行的信息是否已输出完成，如果未完成，那么不能放到out中，否则，out中的数据出现重复，如果已完成，并且命令执行已结束
            # 那么后续不会有新的输出行，所以需要对最后一行判断是否命令已结束。
            rstlast = lines[-1]
            last_line = C.decode_line(rstlast)
            if end_flag is None and C.system_match(last_line):
                success = True
            if end_flag is not None and last_line.find(end_flag) != -1:
                success = True
            if success:
                break
        time.sleep(0.2)
        channel.send_exit_status(0)
        channel.close()
        if len(out) > 0:
            if  C.system_match(out[-1]):
                del out[-1]
        result['out'] = out
        return

    def put_file(self, in_path, out_path):
        """ transfer a file from local to remote """
        C.log.debug("PUT %s TO %s" % (in_path, out_path))
        if not os.path.exists(in_path):
            raise Exception("file or module does not exist: %s" % in_path)
        try:
            self.sftp = self.ssh.open_sftp()
        except Exception as e:
            raise Exception("failed to open a SFTP connection (%s)" % e)
        try:
            self.sftp.put(in_path, out_path)
        except IOError:
            raise Exception("failed to transfer file to %s" % out_path)

    def put_dir(self, remote_dir, local_dir, excludes=[]):
        err_list = []
        try:
            self.sftp = self._connect_sftp()
        except Exception as e:
            raise Exception("failed to open a SFTP connection (%s)", e)
        for file in os.listdir(local_dir):
            # local_dir目录中每一个文件或目录的完整路径
            loc_path_filename = os.path.join(local_dir, file)
            if C.exclude_files(file, loc_path_filename, excludes):
                continue

            # 如果是目录，则递归处理该目录
            if os.path.isdir(loc_path_filename):
                rmt_dir = Path(os.path.join(remote_dir, file)).as_posix()
                try:
                    self.sftp.mkdir(rmt_dir)
                except:
                    pass
                C.log.debug(r'Put文件夹 %s 传输中...' % loc_path_filename)
                self.put_dir(remote_dir=rmt_dir, local_dir=loc_path_filename, excludes=excludes)
            else:
                remote_filename = Path(os.path.join(remote_dir, file)).as_posix()
                C.log.debug(r'  Put文件  %s 传输中...' % loc_path_filename)
                C.log.debug(r'     位置  {file} 传输中...'.format(file=remote_filename))
                try:
                    self.put_file(loc_path_filename, remote_filename)
                except Exception as e:
                    C.log.error(
                        f"Pet文件 {loc_path_filename},{remote_filename} 失败! msg-{e}")
                    err_list.append(loc_path_filename)

        if len(err_list) > 0:
            return False, err_list
        return True, []

    def _connect_sftp(self):
        cache_key = "%s__%s__" % (self.host, self.user)
        if cache_key in SFTP_CONNECTION_CACHE:
            return SFTP_CONNECTION_CACHE[cache_key]
        else:
            result = SFTP_CONNECTION_CACHE[cache_key] = self.connect().ssh.open_sftp()
            return result

    def fetch_file(self, in_path, out_path):
        """ save a remote file to the specified path """
        # vvv("FETCH %s TO %s" % (in_path, out_path), host=self.host)
        try:
            self.sftp = self._connect_sftp()
        except Exception as e:
            raise Exception("failed to open a SFTP connection (%s)", e)
        try:
            self.sftp.get(in_path, out_path)
        except IOError:
            raise Exception("failed to transfer file from %s" % in_path)
    def fetch_dir(self, local_dir, remote_dir, excludes=[]):
        err_list = []
        try:
            self.sftp = self._connect_sftp()
        except Exception as e:
            raise Exception("failed to open a SFTP connection (%s)", e)

        # remote_dir 如果是目录,列出所有目录下的文件及目录循环处理
        for file in self.sftp.listdir_attr(remote_dir):
            remote_path_filename = Path(os.path.join(remote_dir, file.filename)).as_posix()

            # 如果判断为无需下载的文件，则跳过本次循环，处理下一个文件名词
            if C.exclude_files(file.filename, remote_path_filename, excludes):
                C.log.debug('忽略文件%s' % remote_path_filename)
                continue

            # 如果是目录，则递归处理该目录，远端通过stat.S_ISDIR(st_mode)
            if stat.S_ISDIR(file.st_mode):
                tmp_local_dir = os.path.join(local_dir, file.filename)
                if not os.path.exists(tmp_local_dir):
                    os.makedirs(tmp_local_dir)
                self.fetch_dir(local_dir=tmp_local_dir, remote_dir=remote_path_filename, excludes=excludes)
                C.log.debug('Get文件夹%s 传输中...' % remote_path_filename)
                C.log.debug('   位置  {loc_dir}:'.format(loc_dir=tmp_local_dir))
            else:
                tmp_local_filename = os.path.join(local_dir, file.filename)
                try:
                    C.log.debug('  Get文件  %s 传输中...' % remote_path_filename)
                    C.log.debug('   位置  {loc_dir}:'.format(loc_dir=tmp_local_filename))
                    self.fetch_file(remote_path_filename, tmp_local_filename)
                except Exception as e:
                    C.log.error(
                        f"Get文件 {remote_path_filename},{tmp_local_filename} 失败! msg-{e}")
                    err_list.append(remote_path_filename)

        if len(err_list) > 0:
            return False,err_list
        return True,[]

    def close(self):
        """ terminate the connection """
        cache_key = self._cache_key()
        SSH_CONNECTION_CACHE.pop(cache_key, None)
        SFTP_CONNECTION_CACHE.pop(cache_key, None)
        if self.sftp is not None:
            self.sftp.close()
        self.ssh.close()


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

    return exit_status, '', shout, sherr