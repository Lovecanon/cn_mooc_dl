# 中国大学icourse163视频下载工具


### 使用
1. 安装python3：[Download Python | Python.org](https://www.python.org/downloads/)

2. 安装`requests`模块：`pip install requests`

3. 从[github](https://github.com/Lovecanon/cn_mooc_dl)下载代码到本地

4. 解压后进入代码目录执行：`python icourse163_dl.py http://www.icourse163.org/course/NUDT-1001616011?tid=1001690014#/info`

    开始下载...

### 效果
![image](https://github.com/Lovecanon/cn_mooc_dl/raw/master/capture/downloading.gif)

### 说明
1. 程序自动选择视频清晰度，顺序：超高清(`mp4ShdUrl`, `flvShdUrl`),高清(`mp4HdUrl`, `flvHdUrl`),标清(`mp4SdUrl`, `flvSdUrl`)

2. 文件默认下载到当前目录

3. `python icourse163_dl.py --help` 查看帮助信息


### 更新
##### 2019-8-5
* 解决部分使用`http://v.stu.126.net`的课程无法下载
* 重命名本地视频文件名
* 输出课程目录

##### 2017-11-17
* 命令行参数指定只下载课件：`--doc-only`
* 课件下载
* 模拟登陆，获取`NTESSTUDYSI`；在请求课程详情时设置`NTESSTUDYSI`(网易并未校验)


***

##### 如有问题，欢迎在[issues](https://github.com/Lovecanon/cn_mooc_dl/issues)中提出






