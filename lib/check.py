from lib.tools import Tools
import paramiko
import logging
from lib.Logger import logger

class checkcfg(object):
    def __init__(self):
        self.mylog = logger('check.log', logging.INFO, logging.INFO)

    def checkCfgConnect(self, cfg):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        pkey = paramiko.RSAKey.from_private_key_file(password=cfg["public"]["passphrase"], filename=cfg["public"]["key_filename"])
        for host in cfg["HOST"]:
            if Tools().connectWithRSA(ssh, host["ip"], host["username"], pkey, timeout=1):
                self.mylog.info("连接服务器" + host["username"] + "@" + host["hostname"] + "成功")
            else:
                self.mylog.info("连接服务器" + host["username"] + "@" + host["hostname"] + "不成功")
        ssh.close()

    def checkCfgHostname(self, cfg):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        pkey = paramiko.RSAKey.from_private_key_file(password=cfg["public"]["passphrase"],
                                                     filename=cfg["public"]["key_filename"])
        for host in cfg["HOST"]:
            if Tools().connectWithRSA(ssh, host["ip"], host["username"], pkey, timeout=1):
                if Tools().checkHostName(ssh, host["hostname"], '', timeout=1):
                    self.mylog.info("服务器" + host["hostname"] + "主机名一致")
                else:
                    self.mylog.info("服务器" + host["hostname"] + "主机名不一致")
            else:
                self.mylog.info("连接服务器" + host["username"] + "@" + host["hostname"] + "不成功")
        ssh.close()


