# 生产hosts.yaml

test.txt 模板

| 主机名 | 应用用户1 | 应用用户2 | 应用用户3 | 应用用户4 | 应用用户5 | IP地址 |
| ------ | --------- | --------- | --------- | --------- | --------- | ------ |
|        |           |           |           |           |           |        |
|        |           |           |           |           |           |        |

```shell
awk '{a=0} $NF ~ /[0-9]+.[0-9]+.[0-9]+.[0-9]+/ {a=1} a==1 && NF >= 3 {printf "%s:\n  ip: %s\n  username: %s\n",$1,$NF,$2 } a ==1 && NF >= 4 {printf "%s-%s:\n  ip: %s\n  username: %s\n",$1,$3,$NF,$3} a==1 && NF >= 5 {printf "%s-%s:\n  ip: %s\n  username: %s\n",$1,$4,$NF,$4 } a==1 && NF >= 6 {printf "%s-%s:\n  ip: %s\n  username: %s\n",$1,$5,$NF,$5} a==1 && NF >= 7 {printf "%s-%s:\n  ip: %s\n  username: %s\n",$1,$6,$NF,$6 }'  test.txt > hosts.yaml


awk '{a=0} $NF ~ /[0-9]+.[0-9]+.[0-9]+.[0-9]+/ {a=1} a==1 && NF == 3 {printf "%s-%s:\n  ip: %s\n  username: %s\n",$1,$2,$NF,$2 } a==1 && NF > 3 {printf "%s-%s:\n  ip: %s\n  username: %s\n",$1,$2,$NF,$2 } a ==1 && NF >= 4 {printf "%s-%s:\n  ip: %s\n  username: %s\n",$1,$3,$NF,$3} a==1 && NF >= 5 {printf "%s-%s:\n  ip: %s\n  username: %s\n",$1,$4,$NF,$4 } a==1 && NF >= 6 {printf "%s-%s:\n  ip: %s\n  username: %s\n",$1,$5,$NF,$5} a==1 && NF >= 7 {printf "%s-%s:\n  ip: %s\n  username: %s\n",$1,$6,$NF,$6 }'  test.txt > hosts.yaml
```


# 生成groups.yaml

`grep '^[a-z]' hosts.yaml | sed -r 's/(...)(.*):/\U\1-GROUP:/' | sort | uniq  >> groups.yaml`
`grep '^[a-z]' hosts.yaml >> tmp_hosts.txt`

```bash
#!/bin/bash
# 文件名gen_groups.sh
# 使用bash gen_groups.sh 执行
host_fl='tmp_hosts.txt'
group_fl='groups.yaml'

i=0
while read line
do
	group_pre=$(echo "${line:0:3}-GROUP"|tr  '[a-z]' '[A-Z]')
	sed -i "/${group_pre}/a\  - ${line}" ${group_fl}

	i=$(($i+1))
	if [ $i -ge 5000 ]; then
	    exit
	fi
done< $host_fl
```