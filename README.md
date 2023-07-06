# Tansible

#### 介绍
批量管理远程服务器工具

#### 软件架构
python paramiko 


#### 安装教程

1.  pyinstaller  genarate.spec 生成二进制文件


#### 使用说明

1. config/hosts.yaml 文件中创建主机相关信息
2. config/groups.yaml 中创建主机组群相关信息，可将部分主机设定为一个组，方便后面的action文件调用
3. 按需创建action文件，action.yaml是默认文件，文件名称可自定义
    - cmd>Tansible.exe #运行的是action.yaml中的配置
    - cmd>Tansible.exe test.yaml #运行的是config/test.yaml 中的配置
4. 建议创建指定bat文件，关联action文件，以方便执行相关任务
5. 单步运行模式增加 -s 选项如 cmd>Tansible.exe test.yaml -s 

#### hosts.yaml文件配置说明
该文件的配置信息主要用于连接远程机器用，如主机名、IP、用户名，密码或秘钥文件等信息，目前支持的配置信息如下。

- key_filename：秘钥文件
- passphrase：秘钥文件的密码，如果秘钥文件没有密码则可配置为空或任意字符
- connect_type：连接远程主机的方式，1为使用用户名密码连接，2为使用用户名秘钥文件连接
- username：用户名
- password：密码
- 主机名：一般配置为主机名，如果有多用户，则配置为主机名-用户名

```yaml
PUBLIC:
    #公共参数部分,如果HOST部分有相关配置，则优先使用HOST的配置
    # 秘钥文件
    key_filename: config/id_rsa
    # 秘钥文件密码
    passphrase: 123
    # 连接方式 1 表示采用密码的方式，2 表示采用秘钥文件的方式
    connect_type: 2  # 1 password  2 rsa
    # 用户名
    username: root
    # 密码
    password: password
HOST:
  #  一般配置为主机名，如果有多用户则配置为主机名-用户名
  host1:
    ip: 127.0.1.131
  host2:
    ip: 127.0.1.132
  host3:
    ip: 192.168.128.140
    connect_type: 1
    username: root
    password: redhat123
  host4:
    ip: 192.168.128.141
    connect_type: 1
  zbx-a:
    ip: 192.168.128.141
    connect_type: 1
  zbx-b:
    ip: 192.168.128.141
    connect_type: 1
```

#### groups.yaml文件配置说明
对同类机器进行创建群组，方便后面的action文件调用，组分为简单组和嵌套组，简单组下面为具体的主机名，嵌套组下面还可以包含其它的组

```yaml
# 简单组
group1:
  - host1
  - host2
# 简单组，组下面的主机名可以支持lable[x:y]范围设定及fnmatch.fnmatchcase的linux类文件名模糊匹配 
group2:
  - host[3:4]
  - zbx*
# 嵌套组
apart:
  # 嵌套组，则组下面必须为字典类型，且Key必须为children，children下面必须为简单组
  children:
    - group1
    - group2
```

#### action文件配置说明
```yaml
PUBLIC:
  # 公共设置部分
  公共参数key: 公共参数value
  # exception_deal 异常处理参数，c continu 表示忽略错误，继续执行，程序最后会打印忽略列表,e exit 表示退出Tansible程序,
  # r rerun 表示重新执行该任务,q question 表示询问, 如果未配置exception_deal参数，则Tansible程序以
  # q question的方式每次遇到异常时进行询问
  exception_deal: q
  # max_worker 表示并发线程数，可选参数，不配置时默认时1
  max_worker: 4
ACTION:
  - hosts: [Simutransaction1, Simutransaction2,'macs[1:16]', 'tra*']  
    # hosts: ALL 表示对hosts.yaml中所有主机执行任务，支持lable[x:y]范围设定及fnmatch.fnmatchcase的linux类文件名模糊匹配，
    # 如MACS[1:16]表示MACS1、MACS2、MACS3...一直到MACS16的主机，也可配置为group.yaml中的组
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
    例：
    GetHostList:
###### CheckConnect, 检查SSH连接
*模块参数*

    # 无
    例：
    CheckConnect:
###### CheckHostname, 检查hosts.yaml与实际主机名
*模块参数*

```yaml
# 运程执行命令获取主机名
# cmd 为可选参数，当hosts.yaml中配置的主机名与hostname命令结果不一致时，可利用cmd来调整
例1：
CheckHostname:
例2：
CheckHostname:
  cmd: 'echo $(hostname)-$USER'
```
###### DbPwdModify，数据库密码配置文件调整，单个文件
*模块参数*

```yaml
# 该模块提供单个密码配置文件的下载，并修改密码，提供下载改密码、发布新配置文件及回滚功能
# 下载到download\dbpwdmodify 目录下
# action 提供DOWNLOAD,UPLOAD,ROLLBACK选项，分别为下载改密，发布及回滚功能
例1：
DbPwdModify:
   cfg_file : /home/xx/yy/webapps/ROOT/WEB-INF/conf/application-jdbc.properties 
   instr: 'spring.datasource.password=' 
   pwd: BlowFish
   action:
     - DOWNLOAD
```

###### DbPwdModifys，数据库密码配置文件调整，多个文件
*模块参数*

```yaml
# 该模块提供多个密码配置文件的下载，并修改密码，提供下载改密码、发布新配置文件及回滚功能
# 下载到download\dbpwdmodify 目录下
# action 提供DOWNLOAD,UPLOAD,ROLLBACK选项，分别为下载改密，发布及回滚功能
# cfg_file 具体配置服务器上密码配置文件的路径和文件名
# instr 用于查找行，并对instr字符后面的内容用新的密码进行替换
# pwd 设置新密码
例1：下载并转换服务器中 /home/xx/mntrad/application-jdbc.properties到download\dbpwdmodify\主机名\mntrad目录下，下载并转换服务器中 /home/xx/quote/application-jdbc.properties到download\dbpwdmodify\主机名\quote目录下
DbPwdModifys:
    mntrad:       
        cfg_file: /home/xx/mntrad/application-jdbc.properties       
        instr: 'spring.datasource.password='        
        pwd: BlowFish
    quote:
        cfg_file: /home/xx/quote/application-jdbc.properties
        instr: 'spring.datasource.password='
        pwd: BlowFish
    action:
        - DOWNLOAD
```
###### SysPwdModify，系统用户密码调整
*模块参数*

```yaml
# 该模块提供系统用户密码修改功能，current_pwd_file优先级大于current_pwd,
# new_pwd_file优先级大于new_pwd
# current_pwd 所有主机的当前密码一样时进行配置
# action 方式
    #   checkcur 检查当前密码
    #   checknew 检查新密码
    #   modify 改密码
例1：当前密码统一，新密码统一，检查当前密码
SysPwdModify:
    current_pwd: 当前密码   
    new_pwd: 新密码        
    action: checkcur
例2：当前密码不统一，新密码不统一，修改密码
SysPwdModify:
    current_pwd_file: current_pwd_file.yaml   
    new_pwd_file: new_pwd_file.yaml        
    action: modify    
```
###### Tsftp，上传下载模块
*模块参数*

```yaml
# 该模块提供下载，上传功能        
# action 提供download,upload选项，分别为下载，上传
local_dir: 可选参数，本地存放路径，如果不设置则默认下载到download\Tsftp 目录下
# conf 子文件夹名称，如果设置为{HOME}或者NO_DIR则表示不建子文件夹
conf:
    #remote_dir 远程路径 ，文件夹的以/结尾，下载模式支持*模糊匹配,$HOME表示/home/用户名，注意目录的配置需要以/结尾
    # $USER表示host.yaml中的username,$HOSTNAME表示host.yaml中的主机名
    # 上传时将download\Tsftp\主机名\子文件夹\ 下面的文件上传到remote_dir
    # 设置的文件夹中，如果remote_dir中是文件格式，则去掉最后文件名只取目录
    remote_dir: /home/xx/ 
    # include可选参数，该参数只对下载有用，只有在remote_dir 为文件夹（以/结尾）时，才支持include设置,否则无效   
    include: [yy, zz]  
    # 可选参数，该参数只对下载有用
    exclude: [logs, log, csdklog, '*log', nohup.out] 
action: download 
例1：下载服务器上的/home/xx/ 到默认下载目录中
Tsftp:
   NO_DIR:
      remote_dir: /home/xx/ 
   action: download
例２：上传本地路径download\Tsftp\主机名\ 到主机服务器上的/home/xx/目录
Tsftp:
   NO_DIR:
      remote_dir: /home/xx/ 
   action: upload      
```
###### Tshell，远程执行命令模块
*模块参数*

```yaml
# 该模块提供运程执行命令的功能
cmd: 'hostname'
例1：查看主机名
Tshell:
  cmd: hostname
```

###### Tsupershell，远程执行命令模块
可进行交互式操作，instr和input列表里面的个数必须一致，instr[0]的输入为input[0]
*模块参数*
```yaml 
# 命令参数，必须填写
cmd: 'scp abd.tar 192.168.0.1:/dir'
# 可选参数，交户输入前提示的信息
instr: ['yes/no', 'password']
# 可选参数，交互输入的参数
input: ['yes', '密码']
例1：scp 主机中/abd.tar 文件到 192.168.0.1:/dir 中
Tsupershell:
    cmd: 'scp abd.tar 192.168.0.1:/dir'
    instr: ['yes/no', 'password']
    input: ['yes', '密码']

```
###### Tupload，上传模块
*模块参数*

```yaml
# 该模块提供上传文件的功能
simple_type: 1 # 0  source_dir下根据主机名文件夹上传， 1 直接source_dir
source_dir: E:/PyCharmProject/Tansible/download/Tsftp/MACS1/  #目录以linux格式设置
dest_dir: /root/upload/  #上传目的路径,$HOME表示/home/用户名,$USER表示用户名（host.yaml中的username）,注意目录需要以/结束，如果需要上传多个路径可以用[路径1,路径2，路径3]的形式
exclude: [start.sh]      #不上传的文件及文件夹列表

例1：将package目录下的文件上传到/root/upload/目录中
Tupload:
    simple_type: 1 
    source_dir: package
    dest_dir: /root/upload/
```
###### Tvsget，版本下载模块，大文件获取size，mtime，st_mode
*模块参数*

```yaml
# 该模块提供下载功能，用于版本对比，文件大小大于md5filter的将获取文件的大小、修改时间及st_mode，而不下载文件
local_dir: 可选参数, 本地存放路径，可选，如果不设置则默认下载到download\Tsftp 目录下
# 子文件夹名称，如果设置为{HOME}或者NO_DIR则表示不建子文件夹
mntrad: 
    # remote_dir 远程下载路径 ，文件夹的已/结尾，支持*模糊匹配           
    remote_dir: /home/xx/ 
    # exclude 可选参数
    exclude: [不下载的文件在这里] 
    # md5filter文件大于该值则不下载文件而是获取文件的大小、修改时间及st_mode
    md5filter: 30000  
    # bigcontent 可选参数，可设置"size", "mtime", "st_mode",不配置则默认全部获取
    bigcontent:  size 
```
###### Tvsget1，版本下载模块，大文件获取MD5码
*模块参数*

```yaml
# 该模块提供下载功能，用于版本对比，文件大小大于md5filter的将获取文件的md5码，而不下载文件
local_dir: 可选参数,本地存放路径，如果不设置则默认下载到download\Tvsget1 目录下
# 子文件夹名称，如果设置为{HOME}或者NO_DIR则表示不建子文件夹
mntrad: 
    # remote_dir 远程下载路径 ，文件夹必须以“/”结尾，支持*模糊匹配
    remote_dir: /home/sgeapp/ 
    # exclude 可选参数
    exclude: [不下载的文件在这里] 
    # md5filter 文件大于该值则不下载文件而是获取文件的md5码
    md5filter: 30000   
```


#### 参与贡献

1.  Fork 本仓库
2.  新建 Feat_xxx 分支
3.  提交代码
4.  新建 Pull Request

model 模板

模板文件位置：model/模块名称/模块名称.py

```python
# 模块的类名称固定为ModelClass,必须包含__init__初始化函数及action动作函数
class ModelClass(object):
    # 初始化函数，必须包括lib.Logger类mylog ,用于日志记录的
    def __init__(self, mylog):
        self.mylog = mylog
        # self.mylog 为lib.Logger.py 中的类，用法如下：
        
        # self.mylog.debug('一个debug信息')
        # self.mylog.info('一个info信息')
        # self.mylog.war('一个warning信息')
        # self.mylog.error('一个error信息')
        # self.mylog.cri('一个致命critical信息')
    # 实际动作函数，必须包括如下的参数
    def action(self, ssh, hostname, param, hostparam=None):
        # ssh 会话连接
        # hostname 主机名
        # param 模块参数
        # hostparam 主机参数，参考host.yaml
        pass
```

