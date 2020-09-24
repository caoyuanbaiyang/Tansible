# Tansible

#### 介绍
批量管理远程服务器工具

#### 软件架构
paramiko 


#### 安装教程

1.  pyinstaller  genarate.spec 生成二进制文件


#### 使用说明

1.  hosts.yaml 文件中创建主机相关信息
2.  groups.yaml 中创建主机组群相关信息，可将部分主机设定为一个组，方便后面的action文件调用
3.  按需创建action文件，action.yaml是默认文件，文件名称可自定义
4.  建议创建指定bat文件，关联action文件，以方便执行相关任务

#### action文件配置说明
```yaml
PUBLIC:
  # 公共设置部分
  公共参数key: 公共参数value
ACTION:
  - hosts: [Simutransaction1, Simutransaction2]  
    # hosts: ALL 表示对hosts.yaml中所有主机执行任务，支持lable[x:y]范围设定
    tasks:
      - name: 任务说明
        SysPwdModify:  # 调用的模块，下面的设置都是模块相关的设置       
          模块参数1: 模块参数1value
          模块参数2: 模块参数2value
```

##### 模块说明
###### GetHostList, 获取主机列表
*模块参数*

        # 无
###### CheckConnect, 检查SSH连接
*模块参数*

        # 无
###### CheckHostname, 检查hosts.yaml与实际主机名
*模块参数*

        # 无
###### DbPwdModify，数据库密码配置文件调整，单个文件
*模块参数*

```yaml
    # 该模块提供单个密码配置文件的下载，并修改密码，提供下载改密码、发布新配置文件及回滚功能
    # 下载到download\dbpwdmodify 目录下
    # action 提供DOWNLOAD,UPLOAD,ROLLBACK选项，分别为下载改密，发布及回滚功能
      cfg_file : /home/xx/yy/webapps/ROOT/WEB-INF/conf/application-jdbc.properties 
      instr: 'spring.datasource.password=' 
      pwd: *BlowFish
      action:
        - DOWNLOAD
```

###### DbPwdModifys，数据库密码配置文件调整，多个文件
*模块参数*

```yaml
    # 该模块提供多个密码配置文件的下载，并修改密码，提供下载改密码、发布新配置文件及回滚功能
    # 下载到download\dbpwdmodify 目录下
    # action 提供DOWNLOAD,UPLOAD,ROLLBACK选项，分别为下载改密，发布及回滚功能
      mntrad:
        # cfg_file 具体配置服务器上密码配置文件的路径和文件名
        cfg_file: /home/xx/yy/webapps/ROOT/WEB-INF/conf/application-jdbc.properties
        # instr 用于查找行，并对instr字符后面的内容用新的密码进行替换
        instr: 'spring.datasource.password='
        # pwd 设置新密码
        pwd: *BlowFish
      quote:
        cfg_file: /home/xx/yy/webapps/quote/WEB-INF/conf/application-jdbc.properties
        instr: 'spring.datasource.password='
        pwd: *BlowFish
      action:
        - DOWNLOAD
```
###### SysPwdModify，系统用户密码调整
*模块参数*

```yaml
    # 该模块提供系统用户密码修改功能，current_pwd_file优先级大于current_pwd,
    # new_pwd_file优先级大于new_pwd
      current_pwd: 当前密码   # 所有主机的当前密码一样
      new_pwd: 新密码        # 所有主机的新密码一样
      current_pwd_file:  current_pwd_file.yaml #当每个主机的密码不一样时，采用文件保存当前密码
      new_pwd_file:  new_pwd_file.yaml #当每个主机的密码不一样时，采用文件保存新密码
      # action 方式
      #   checkcur 检查当前密码
      #   checknew 检查新密码
      #   modify 改密码
      action: checkpwd
```
###### Tsftp，上传下载模块
*模块参数*

```yaml
    # 该模块提供下载，上传功能        
    # action 提供download,upload选项，分别为下载，上传
      local_dir: 可选参数，本地存放路径，如果不设置则默认下载到download\Tsftp 目录下
      '{HOME}': # 子文件夹名称，如果设置为{HOME}则表示不建子文件夹
        remote_dir: /home/xx/ #远程下载路径 ，文件夹的已/结尾，支持*模糊匹配,$HOME表示/home/用户名/
        include: [yy, zz]  # 可选参数，该参数只对下载有用
        exclude: [logs, log, csdklog, '*log', nohup.out] # 可选参数
      action: download 
```
###### Tshell，远程执行命令模块
*模块参数*

          # 该模块提供运程执行命令的功能
          cmd: 'hostname'
###### Tupload，上传模块
*模块参数*

```yaml
      # 该模块提供上传文件的功能
      simple_type: 1 # 0  source_dir下根据主机名文件夹上传， 1 直接source_dir
      source_dir: E:/PyCharmProject/Tansible/download/Tsftp/MACS1/  #目录以linux格式设置
      dest_dir: /root/upload/  #上传目的路径
      exclude: [start.sh]      #不上传的文件及文件夹列表
```
###### Tvsget，版本下载模块，大文件获取size，mtime，st_mode
*模块参数*

```yaml
    # 该模块提供下载功能，用于版本对比，文件大小大于md5filter的将获取文件的大小、修改时间及st_mode，而不下载文件
    local_dir: 可选参数, 本地存放路径，可选，如果不设置则默认下载到download\Tsftp 目录下
      mntrad: # 子文件夹名称，如果设置为{HOME}则表示不建子文件夹
        remote_dir: /home/xx/ #远程下载路径 ，文件夹的已/结尾，支持*模糊匹配           
        exclude: [不下载的文件在这里] # 可选参数
        md5filter: 30000  # 文件大于该值则不下载文件而是获取文件的大小、修改时间及st_mode
        bigcontent:  size # 可选参数，可设置"size", "mtime", "st_mode",不配置则默认全部获取
```
###### Tvsget1，版本下载模块，大文件获取MD5码
*模块参数*

```yaml
    # 该模块提供下载功能，用于版本对比，文件大小大于md5filter的将获取文件的md5码，而不下载文件
    local_dir: 可选参数,本地存放路径，如果不设置则默认下载到download\Tvsget1 目录下
      mntrad: # 子文件夹名称，如果设置为{HOME}则表示不建子文件夹
        remote_dir: /home/sgeapp/ #远程下载路径 ，文件夹必须以“/”结尾，支持*模糊匹配
        exclude: [不下载的文件在这里] # 可选参数
        md5filter: 30000   # 文件大于该值则不下载文件而是获取文件的md5码
```


#### 参与贡献

1.  Fork 本仓库
2.  新建 Feat_xxx 分支
3.  提交代码
4.  新建 Pull Request

model 模板

```python
# 模块的类名称固定为ModelClass,必须包含__init__初始化函数及action动作函数
class ModelClass(object):
    # 初始化函数，必须包括lib.Logger类mylog ,用于日志记录的
    def __init__(self, mylog):
        self.mylog = mylog
    # 实际动作函数，必须包括如下的参数
    def action(self, ssh, hostname, param, hostparam=None):
        # ssh 会话连接
        # hostname 主机名
        # param 模块参数
        # hostparam 主机参数，参考host.yaml
```
self.mylog 用法如下：

```python
self.mylog.debug('一个debug信息')
self.mylog.info('一个info信息')
self.mylog.war('一个warning信息')
self.mylog.error('一个error信息')
self.mylog.cri('一个致命critical信息')
```
