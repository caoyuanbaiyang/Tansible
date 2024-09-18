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
import stat
import time
from pathlib import Path

import select

import lib.constants as C

# prevent paramiko warning noise -- see http://stackoverflow.com/questions/3920502/
import paramiko

# keep connection objects on a per host basis to avoid repeated attempts to reconnect

SSH_CONNECTION_CACHE = {}
SFTP_CONNECTION_CACHE = {}


class Connection(object):
    """ SSH based connections with Paramiko """

    def __init__(self, host, user, conn_type, password=None, key_filename=None, passphrase=None, port=22, timeout=3000):

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

    def exec_command(self, cmd, executable='/bin/sh'):
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
        C.logger.debug(f"EXEC {quoted_command} at {self.host}")
        chan.exec_command(quoted_command)

        stdout = []
        stderr = []

        # Read stdout
        _ready = chan.recv_ready()
        while not _ready:
            _ready, _, _ = select.select([chan], [], [], timeout)
            time.sleep(0.1)
            print('sleep 0.1')

        while chan.recv_ready():
            data = chan.recv(bufsize)
            stdout.append(data)
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

    def put_file(self, in_path, out_path):
        """ transfer a file from local to remote """
        C.logger.debug("PUT %s TO %s" % (in_path, out_path))
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
                C.logger.debug(r'Put文件夹 %s 传输中...' % loc_path_filename)
                self.put_dir(remote_dir=rmt_dir, local_dir=loc_path_filename, excludes=excludes)
            else:
                remote_filename = Path(os.path.join(remote_dir, file)).as_posix()
                C.logger.debug(r'  Put文件  %s 传输中...' % loc_path_filename)
                C.logger.debug(r'     位置  {file} 传输中...'.format(file=remote_filename))
                try:
                    self.put_file(loc_path_filename, remote_filename)
                except Exception as e:
                    C.logger.error(
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
                C.logger.debug('忽略文件%s' % remote_path_filename)
                continue

            # 如果是目录，则递归处理该目录，远端通过stat.S_ISDIR(st_mode)
            if stat.S_ISDIR(file.st_mode):
                tmp_local_dir = os.path.join(local_dir, file.filename)
                if not os.path.exists(tmp_local_dir):
                    os.makedirs(tmp_local_dir)
                self.fetch_dir(local_dir=tmp_local_dir, remote_dir=remote_path_filename, excludes=excludes)
                C.logger.debug('Get文件夹%s 传输中...' % remote_path_filename)
                C.logger.debug('   位置  {loc_dir}:'.format(loc_dir=tmp_local_dir))
            else:
                tmp_local_filename = os.path.join(local_dir, file.filename)
                try:
                    C.logger.debug('  Get文件  %s 传输中...' % remote_path_filename)
                    C.logger.debug('   位置  {loc_dir}:'.format(loc_dir=tmp_local_filename))
                    self.fetch_file(remote_path_filename, tmp_local_filename)
                except Exception as e:
                    C.logger.error(
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
