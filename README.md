### 1.需要
* 装有python3的电脑；
* requests库；
```bash
  pip install requests
```
* 代码：https://github.com/Lovecanon/cn_mooc_dl
* 课程主页地址的参数部分
e.g http://www.icourse163.org/course/NUDT-1001616011?tid=1001690014#/info  
只需要：NUDT-1001616011?tid=1001690014参数部分


### 2.开始：
cmd进入icourse163_dl.py所在目录并运行；
```bash
'''
    默认视频下载到当前icourse163_dl.py所在目录中；
    下载速度时快时慢，可以Ctrl+C中断下载，重新会接着上次下载的地方下载。
'''
python icourse163_dl.py --username=535036628@qq.com --password=aikechengp --params=UESTC-238011?tid=1001757010

'''
    如果使用默认的账号535036628@qq.com，你只需要添加一个课程链接参数即可。
'''
python icourse163_dl.py --params=UESTC-238011?tid=1001757010
```


#### 注：有些链接不带tid
F12开发者工具---->刷新页面---->找到'CourseBean.checkTermLearn.dwr'请求---->tid就在该请求c0-param0参数中。


## TODO  
tid参数有些累赘，
