## 中国大学icourse163视频下载工具

#### 更新
* pdf课件一并下载
* 前置登陆，获取`NTESSTUDYSI`；在请求课程详情时设置`NTESSTUDYSI`(网易并未校验)

#### 安装指南
1. 安装python3

    https://www.python.org/downloads/

2. 安装`requests`模块

        pip install requests

3. 下载代码到本地，进入项目主页：`Clone and download` --> `Download ZIP`

#### 下载

CMD进入本地该项目目录，查看帮助信息。其中只有一个必选参数：`-c`即：课程链接

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
                                课程主页链接
          -o OUTPUT, --output OUTPUT
                                文件下载路径，默认：当前路径


进入`icourse163`的课程主页，e.g.`http://www.icourse163.org/course/NUDT-1001616011?tid=1001690014#/info`,
复制链接中`NUDT-1001616011?tid=1001690014`。

注：有些课程链接中可能没有`tid`参数，提供两种获取方法：
* 在课程页面右侧，选中`第n次开课`，这时候链接就会出现`tid`
* 在课程页面，鼠标右键：查看网页源码(Ctrl+u), 搜索(Ctrl+f)`termId`将后面的数字复制下来拼凑起来即可


运行，下载`TONGJI-47017?tid=44002`课程到`E://`目录下，文件保存方式类似于下面日志打印的格式
![image](https://github.com/Lovecanon/cn_mooc_dl/raw/master/capture/downloading.gif)

#### 几点说明
* 视频清晰度

视频清晰度优先选择超高清(`mp4ShdUrl`, `flvShdUrl`),高清(`mp4HdUrl`, `flvHdUrl`),标清(`mp4SdUrl`, `flvSdUrl`)。如果需要调整下载视频的清晰度，删除
代码中常量`RESOLUTION_TYPES`其他清晰度元素即可。

* `tid.json`文件

下载开始后，本地课程目录会出现一个`tid.json`的文本文件，该文件保存了课程信息的组织方式及资源地址，再次下载会直接读取`tid.json`文件，
避免不必要的网络请求。


* 代码修改之后还没有进行整个课程的下载测试，如有问题欢迎在[issues](https://github.com/Lovecanon/cn_mooc_dl/issues)中提出


TODO
----
- [x] 移除`tid`参数，或使用者直接传入课程链接即可解析，下载
注：
`http://www.icourse163.org/course/NUDT-1001616011`
`http://www.icourse163.org/course/NUDT-1001616011?tid=1001690014#/info`
`NUDT-1001616011?tid=1001690014`
三种情况都可以正常解析，无需再手动查找tid参数。
- [x] 从已保存的`tid.json`文件中加载，视频清晰度与上次下载时一致。
注：移除视频清晰度选择项


如有问题，欢迎在[issues](https://github.com/Lovecanon/cn_mooc_dl/issues)中提出
-------------------------------------------------------------------





