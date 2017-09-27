## 中国大学icourse163视频下载工具

#### 更新
* 前置登陆，获取`NTESSTUDYSI`；在请求课程详情时设置`NTESSTUDYSI`

#### 安装指南
1. 安装python3

    https://www.python.org/downloads/

2. 安装`requests`模块

        pip install requests

3. 下载代码到本地，进入项目主页：`Clone and download` --> `Download ZIP`

#### 下载

CMD进入本地该项目目录，查看帮助信息。其中只有一个必选参数：`-c`即：课程信息参数

        D:\download\cn_mooc_dl>python icourse163_dl.py --help
        usage: icourse163_dl.py [-h] [-u USERNAME] [-p PASSWD] -c COURSE [-o OUTPUT]
                                [-r RESOLUTION]

        optional arguments:
          -h, --help            show this help message and exit
          -u USERNAME, --username USERNAME
                                第三方登陆网站爱课程的用户名, 默认:535036628@qq.com
          -p PASSWD, --passwd PASSWD
                                第三方登陆网站爱课程的密码, 默认:aikechengp
          -c COURSE, --course COURSE
                                链接中的课程信息，如:TONGJI-47017?tid=44002
          -o OUTPUT, --output OUTPUT
                                文件下载路径，默认：当前路径
          -r RESOLUTION, --resolution RESOLUTION
                                视频清晰度，shd:超清, hd:高清, sd:标清, 默认:shd


进入`icourse163`的课程主页，e.g.`http://www.icourse163.org/course/NUDT-1001616011?tid=1001690014#/info`,
复制链接中`NUDT-1001616011?tid=1001690014`。

注：有些课程链接中可能没有`tid`参数，提供两种获取方法：
* 在课程页面右侧，选中`第n次开课`，这时候链接就会出现`tid`
* 在课程页面，鼠标右键：查看网页源码(Ctrl+u), 搜索(Ctrl+f)`termId`将后面的数字复制下来拼凑起来即可


运行，下载`TONGJI-47017?tid=44002`课程到`E://`目录下，文件保存方式类似于下面日志打印的格式

        D:\download\cn_mooc_dl>python icourse163_dl.py -c TONGJI-47017?tid=44002 -o E://
        2017-09-27 11:11:51 INFO login success...
        2017-09-27 11:11:51 INFO 第0讲_导学篇
        2017-09-27 11:11:51 INFO     导学篇
        2017-09-27 11:11:51 INFO         导学篇.mp4
        2017-09-27 11:11:51 INFO         导学篇PDF.pdf
        2017-09-27 11:11:51 INFO     讨论
        2017-09-27 11:11:51 INFO 第1讲_计算机文化与计算思维基础
        2017-09-27 11:11:51 INFO     1.1_引言
        2017-09-27 11:11:51 INFO         引言.mp4
        ...
        2017-09-27 11:11:57 INFO         程序设计语言1.mp4
        2017-09-27 11:11:57 INFO         程序设计语言2.mp4
        2017-09-27 11:11:57 INFO         程序设计语言.pdf.pdf
        2017-09-27 11:11:57 INFO [downloading] 导学篇.mp4 ---> E://TONGJI-47017\第0讲_导学篇\导学篇
        [                                                  ] 0%  102.22MB at 971.42KB/s
        [                                                  ] 1%  102.22MB at 896.14KB/s
        [>                                                 ] 2%  102.22MB at 760.81KB/s


#### 几点说明
* `tid.json`文件

下载开始后，本地课程目录会出现一个`tid.json`的文本文件，该文件保存了课程信息的组织方式及资源地址，再次下载会直接读取`tid.json`文件，
避免不必要的网络请求。



TODO
----
* 移除`tid`参数，或使用者直接传入课程链接即可解析，下载
* 从已保存的`tid.json`文件中加载，视频清晰度与上次下载时一致


如有问题，欢迎在[issues](https://github.com/Lovecanon/cn_mooc_dl/issues)中提出
-------------------------------------------------------------------





