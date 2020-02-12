# -*- coding: utf-8 -*-

import os
import paramiko
import logging
from fnmatch import fnmatchcase as match
import stat


# 用于存储一些公用的方法
class Tools(object):

    def inputChoise(self, cs, reminder):
        i = 1
        print('----------------------------')
        for line in cs:
            print(str(i)+': '+line)
            i = i+1
        while 1 > 0:
            choise = input(reminder+'\n')
            logging.info(r"选择项：%s" % choise)
            try:
                if int(choise) > len(cs) or int(choise) < 0:
                    logging.info('输入参数错误,请重新输入')
                else:
                    return cs[int(choise)-1]
            except ValueError as info:
                if str(info).startswith('invalid literal for int()'):
                    logging.info('输入参数错误,请重新输入')
                    continue
                else:
                    raise

    def connectWithRSA(self, ssh, host, username, pkey, timeout=3):
        try:
            ssh.connect(hostname=host, username=username, pkey=pkey, timeout=timeout)
            return True
        except:
            return False

    def connectWithPWD(self, ssh, host, username, password, timeout=3):
        try:
            ssh.connect(hostname=host, username=username, password=password, timeout=timeout)
            return True
        except:
            return False

    def checkHostName(self, ssh, hostname, stdinfo, timeout=3):
        result = self.execCommand(ssh, "hostname", stdinfo, timeout=timeout)
        if result[1].split("\n")[-2].strip() == hostname:
            return True
        else:
            return False

    def execCommand(self, ssh, command, stdinfo=[], timeout=5):
        try:
            stdin, stdout, stderr = ssh.exec_command("echo $LANG")
            langset = stdout.readlines()[0].replace("\n", "").split(".")[1]
        except paramiko.ssh_exception.SSHException:
            logging.info("LANG获取失败")
            raise Exception("LANG获取失败")
        try:
            stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
            logging.info(command)
            for info in stdinfo:
                stdin.write(info+"\n")
                logging.info(info)
            if stderr.readable():
                err = stderr.read()
                err = err.decode(langset)
            if stdout.readable():
                out = stdout.read()
                out = out.decode(langset)
            logging.info("命令out:"+"".join(out))
        except paramiko.ssh_exception.SSHException:
            logging.info("命令执行失败:"+command)
            return [False, "命令执行失败:"+command]
        except Exception as e:
            logging.info(e)
            logging.info("命令执行失败:"+command)
            return [False, e]
        if len(err) != 0:
            logging.info("命令err:" + "".join(err))
            return [False, "".join(err)]
        return [True, out]

    def downloadFromLinux(self, sftp, local_dir, remote_dir, includes=[], excludes=[], timeout=5):
        if remote_dir[-1] == '/':
            remote_dir = remote_dir[0:-1]

        if len(includes) > 0:
            for include in includes:
                # include 包含模糊匹配的字符

                # include 不支持模糊匹配的情况
                if stat.S_ISDIR(sftp.stat(include).st_mode):
                    # include 与 local_dir的关系
                    if remote_dir in include:
                        tmp_dir = include.replace(remote_dir + '/', '')
                        local_dir1 = os.path.join(local_dir, tmp_dir.lstrip('/'))
                    else:
                        local_dir1 = os.path.join(local_dir, include.lstrip('/'))
                    if not os.path.exists(local_dir1):
                        os.makedirs(local_dir1)
                    logging.info('Get文件夹%s 传输中...' % include)
                else:
                    (filepath, filename) = os.path.split(include)
                    local_dir1 = os.path.join(local_dir, filepath.lstrip('/'))
                    if not os.path.exists(local_dir1):
                        os.makedirs(local_dir1)
                    logging.info('Get文件%s 传输中...' % include)
                self.sftp_get_dir_exclude(sftp, include, local_dir1, excludes)
        else:
            self.sftp_get_dir_exclude(sftp, remote_dir, local_dir, excludes)

    def downloadFromLinux_new(self, ssh, local_dir, remote_dir, includes=[], excludes=[], timeout=5):
        if remote_dir[-1] == '/':
            remote_dir = remote_dir[0:-1]
        # sftp = paramiko.SFTPClient.from_transport(ssh.get_transport())
        # include 支持模糊匹配，需要ls
        if len(includes) > 0:
            for include in includes:
                result = self.execCommand(ssh, command="ls " + include)
                if result[0]:
                    logging.info(type(result[1]))

    def sftp_get_dir_exclude(self, sftp, remote_dir, local_dir, excludes=[]):
        # 去掉路径字符串最后的字符'/'，如果有的话
        if remote_dir[-1] == '/':
            remote_dir = remote_dir[0:-1]

        # remote_dir如果是文件
        if not stat.S_ISDIR(sftp.stat(remote_dir).st_mode):
            (tmp_dir, filename) = os.path.split(remote_dir)
            if not(filename in excludes or x.filename in excludes):
                sftp.get(remote_dir, os.path.join(local_dir, filename))
            return

        # remote_dir 如果是目录,列出所有目录下的文件及目录循环处理
        files = sftp.listdir_attr(remote_dir)
        for x in files:
            filename = remote_dir + '/' + x.filename

            # 如果判断为无需下载的文件，则跳过本次循环，进入下一循环
            if self.notDownloadFiles(x.filename, filename, excludes):
                continue

            # 如果是目录，则递归处理该目录，远端通过stat.S_ISDIR(st_mode)
            if stat.S_ISDIR(x.st_mode):
                tmp_dir = os.path.join(local_dir, x.filename)
                logging.INFO('Get文件夹%s 传输中...' % filename)
                os.mkdir(tmp_dir)
                self.sftp_get_dir_exclude(sftp, filename, tmp_dir, excludes)
            else:
                local_filename = os.path.join(local_dir, x.filename)
                logging.INFO('Get文件  %s 传输中...' % filename)
                sftp.get(filename, local_filename)

    def notDownloadFiles(self, filename, dir_filename, excludes=[]):   # 是否属于不下载的文件判断
        # exclude 为具体配置，支持文件名配置及带目录的配置
        # exclude 的不下载，跳过本次循环，进入下一循环
        if filename in excludes or dir_filename in excludes:
            return True

        # exclude 为模糊配置，配置的话就不下载，跳过本次循环，进入下一循环
        for exclude in excludes:
            if match(filename, exclude) or match(dir_filename, exclude):
                return True

        # 跳过隐藏文件的下载，但是.bash_profile  .bashrc 包含环境信息，需要下载
        if filename.startswith('.') and filename not in ['.bash_profile', '.bashrc']:
            return True
        # 以上情况都不是这返回False
        return False

    def isContrainSpecialCharacter(self,string):
        special_character = r"~!@#$%^&*()_+-*/<>,.[]\/"
        for i in special_character:
            if i in string:
                return True
        return False

    def uploadLinux(self, sftp, local_dir, remote_dir):
        if remote_dir[-1] == '/':
            remote_dir = remote_dir[0:-1]

        # 获取当前指定目录下的所有目录及文件
        files = os.listdir(local_dir)
        for x in files:
            # local_dir目录中每一个文件或目录的完整路径
            filename = os.path.join(local_dir, x)
            # 如果是目录，则递归处理该目录
            if os.path.isdir(filename):
                rmt_dir = remote_dir + '/' + x
                try:
                    logging.info(r'Put文件夹 %s 传输中...' % filename)
                    sftp.mkdir(rmt_dir)
                except:
                    # 如果属性__m_replace_dir设置为Y，服务器文件夹存在则先删除再创建
                    # 文件夹已经存在
                    pass
                self.uploadLinux(sftp, filename, rmt_dir)
            else:
                remote_filename = remote_dir + '/' + x
                logging.info(r'Put文件  %s 传输中...' % filename)
                sftp.put(filename, remote_filename)

    def packHost(self, pub_cfg, host_cfg):
        # 判断连接配置采用何种配置，采用public部分还是采用host部分
        # 采用password 方式还是 采用 pkey方式
        for pub_key in pub_cfg.keys():
            if pub_key not in host_cfg.keys():
                host_cfg[pub_key] = pub_cfg.get(pub_key)

        if "username" not in host_cfg.keys() and "username" not in pub_cfg.keys():
            raise Exception("配置错误，用户名未配置")

        if "password" not in pub_cfg.keys() and "password" not in host_cfg.keys() and "key_filename" not in host_cfg.keys() and "key_filename" not in pub_cfg.keys():
            raise Exception("配置错误，连接方式未配置")


def download():
    from lib.readcfg import ReadCfg
    cfg = ReadCfg().readcfg()
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    pkey = paramiko.RSAKey.from_private_key_file(password=cfg["public"]["passphrase"],
                                                 filename=cfg["public"]["key_filename"])
    if Tools().connectWithRSA(ssh, cfg["HOST"][0]["ip"], cfg["HOST"][0]["username"], pkey):
        # 下载方法
        sftp = paramiko.SFTPClient.from_transport(ssh.get_transport())
        Tools().downloadFromLinux(sftp, local_dir=r'E:\临时文件夹\20191114', remote_dir=r'/home/sgeapp', includes=[r'/home/sgeapp/bak'],excludes=['*.sh'])
        # Tools().downloadFromLinux_new(ssh, local_dir=r'E:\临时文件夹\20191114', remote_dir=r'/home/sgeapp', includes=[r'/home/sgeapp/bak'],excludes=['*.sh'])
        logging.info('Get完成')
        ssh.close()


def upload():
    from lib.readcfg import ReadCfg
    cfg = ReadCfg().readcfg()
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    pkey = paramiko.RSAKey.from_private_key_file(password=cfg["public"]["passphrase"],
                                                 filename=cfg["public"]["key_filename"])
    if Tools().connectWithRSA(ssh, cfg["HOST"][1]["ip"], cfg["HOST"][1]["username"], pkey):
        # 上传
        sftp = paramiko.SFTPClient.from_transport(ssh.get_transport())
        Tools().uploadLinux(sftp, r'E:\临时文件夹\20191114', r'/root/hi')


if __name__ == '__main__':
    mformat = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(level=logging.INFO, format=mformat)
    logging.info('开始')
    cs=Tools().inputChoise(cs=['启动', '停止'], reminder='请选择:')
    print(cs)


