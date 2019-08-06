# -*- coding:utf-8 -*-
"""
下载mooc到本地，目录如下
├── week
│   └── lesson
│       └── lecture
"""
import argparse
import os
import re
import time
import logging
from datetime import datetime
from pprint import pprint
from collections import OrderedDict

import requests

from exceptions import RequestExcetpion, LoginException, ParamsException, ParseException
from utils import clean_filename, resume_download_file

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.78 Safari/537.36',
    'Referer': 'http://www.icourse163.org/',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
}

# 登陆相关
INDEX_URL = 'http://www.icourse163.org'
AKC_LOGIN_URL = 'http://www.icourse163.org/passport/reg/icourseLogin.do'
AKC_USERNAME = '535036628@qq.com'
AKC_PASSWD = 'aikechengp'

# 课程详情链接，包含视频、文档下载链接
COURSE_DETAIL_URL = 'http://www.icourse163.org/dwr/call/plaincall/CourseBean.getLastLearnedMocTermDto.dwr'

# 解析week、lesson等数据
# video:     contentId       id          name        teremId
video_ptn = re.compile(
    'contentId=(\d+);.+contentType=1;.+id=(\d+);.+name=\"(.+)\";.+?resourceInfo=null;s\d+.termId=(\d+);')
# doc(pdf):      contentId
doc_ptn = re.compile(
    'contentId=(\d+);.+contentType=3;.+id=(\d+);.+name=\"(.+)\";.+?resourceInfo=null;s\d+.termId=(\d+);')
# lesson:       name
lesson_ptn = re.compile('chapterId=.+?contentId=null.+?name="(.+?)";s.+?releaseTime=')
# week:      name
week_ptn = re.compile('contentId=null;s.+?lessons.+?name="(.+?)";s.+?published=')

# 获取视频、文档数据
QUERY_FILE_URL = 'http://www.icourse163.org/dwr/call/plaincall/CourseBean.getLessonUnitLearnVo.dwr'
VIDEO_UEL_PTN = re.compile('(\w+)="(.+?)";s')
RESOLUTION_TYPES = ['mp4ShdUrl', 'flvShdUrl', 'mp4HdUrl', 'flvHdUrl', 'mp4SdUrl', 'flvSdUrl']
DOC_URL_PTN = re.compile('textOrigUrl:"(\S+?)",')

PREFIX_LECTURE_INDEX_PTN = re.compile('^[\d.\-_ ]+')

CATALOG_FNAME = '课程目录.txt'

sess = requests.Session()
sess.headers = HEADERS


def retry_request(url, method='POST', data=None, params=None, retries=3, timeout=20, **kwargs):
    curr_retry = 0
    while curr_retry < retries:
        try:
            resp = sess.request(method=method, url=url, data=data, params=params, timeout=timeout, **kwargs)
            if not resp.ok:
                logger.error('response status code error, [%d]%s', resp.status_code, url)
                time.sleep(curr_retry * 3)
                curr_retry += 1
                continue
            return resp
        except Exception as e:
            logger.error('[retry %d]request error,%s', curr_retry, e)
            time.sleep(curr_retry * 3)
            curr_retry += 1
    raise RequestExcetpion('retry request error')


def login(username, password):
    """login icourse163.org by aikecheng account"""
    # pre login for get NTESSTUDYSI Cookie
    retry_request(INDEX_URL, method='GET')

    data = {
        'returnUrl': 'aHR0cDovL3d3dy5pY291cnNlMTYzLm9yZy8=',
        'failUrl': 'aHR0cDovL3d3dy5pY291cnNlMTYzLm9yZy9tZW1iZXIvbG9naW4uaHRtP2VtYWlsRW5jb2RlZD1OVE0xTURNMk5qSTRRSEZ4TG1OdmJRPT0=',
        'savelogin': 'false',
        'oauthType': '',
        'username': username,
        'passwd': password
    }
    try:
        resp = sess.post(AKC_LOGIN_URL, data=data, timeout=20)
    except Exception as e:
        raise LoginException('login request error:%s' % e)
    if username not in sess.cookies.get('STUDY_INFO'):
        raise LoginException('login request success, but login cookies not found')
    logger.info('login success...')


def get_course_id_from_url(url):
    """解析命令行传过来的课程参数

    Args:
        url: 课程链接
    """

    # 匹配这两种URL，获取其中的课程id：NUDT-1003101005
    # https://www.icourse163.org/course/NUDT-1003101005?tid=1003312002
    # https://www.icourse163.org/learn/NUDT-1003101005?tid=1003312002#/learn/announce
    course_id_ptn = re.compile('(?:course|learn)/([A-Z-\d]+)')
    course_id_matcher = course_id_ptn.findall(url)
    if not course_id_matcher:
        raise ParamsException('未找到课程id, %s', url)
    return course_id_matcher[0]


def get_course_base_info(course_id, url):
    """访问课程主页，获取课程信息
    优先使用`第一次开课`的tid，如果传过来的参数是最后一次开课，可能视频只放出来一部分

    """
    course_info = {}  # 课程信息
    standard_course_index_url = 'http://www.icourse163.org/course/{}'
    course_url = standard_course_index_url.format(course_id)
    resp = retry_request(course_url, method='GET')

    # 每次开课都产生一个tid，即：term id
    # 2019-8-6：最新开课可能没有结束，导致获取不到全部视频
    page_tid_ptn = re.compile('id : "(\d+)",\ncourseId : "\d+",\nstartTime : "(\d+)",\nendTime : "(\d+)",')
    url_tid_ptn = re.compile('tid=(\d+)')
    page_tid_matcher = page_tid_ptn.findall(resp.text)
    tids = []
    if page_tid_matcher:
        # 最新的开课可能关闭，无法查看视频资源。如：NUDT-1003101005
        # 最老的开课可能资源没有最新开课资源完善。如：UESTC-234010
        # 本程序采用倒序遍历的方法，首先使用最新的tid
        for tid, start_time, end_time in page_tid_matcher:
            if datetime.fromtimestamp(int(end_time[:-3])) <= datetime.now():
                tids.append(tid)
        print(tids)
    else:
        url_tid_matcher = url_tid_ptn.findall(url)
        if url_tid_matcher:
            tids = url_tid_matcher
        else:
            raise ParamsException('未找到本课程开课id，{}'.format(url))

    # 课程名称
    course_name_ptn = re.compile('courseDto = {\nname:"(.+?)",')
    course_name_matcher = course_name_ptn.findall(resp.text)
    course_name = course_name_matcher[0] if course_name_matcher else course_id

    # 学校名称
    university_name_ptn = re.compile('name:"(.+?)",\nbigLogo:"')
    university_name_matcher = university_name_ptn.findall(resp.text)
    university_name = university_name_matcher[0] if university_name_matcher else None

    # 老师
    teachers_ptn = re.compile('lectorName : "(.+?)",')
    teachers = teachers_ptn.findall(resp.text)

    # 课程分类
    category_ptn = re.compile('name : "(.+?)",\ntype : ')
    category = category_ptn.findall(resp.text)
    course_info.update(course_id=course_id, tids=tids, course_name=course_name,
                       university_name=university_name, teachers=teachers, category=category)
    return course_info


def get_video_doc_url(content_id, file_id, file_type='video'):
    """获取视频、课件的下载地址
    注：在实际的icourse163.org页面上，会通过视频id再次发送一次HTTP请求，获取视频的真实地址

    如果`http://v.stu.126.net/mooc-video` 域名无法下载视频，我们可以通过将`http://v.stu.126.net/mooc-video` 替换成`http://jdvodrvfb210d.vod.126.net/jdvodrvfb210d`

    :param content_id:
    :param file_id:
    :param file_type:
    :return:
    """
    file_type_number = '1' if file_type == 'video' else '3'
    data = {
        'callCount': '1',
        'scriptSessionId': '${scriptSessionId}190',
        'httpSessionId': sess.cookies.get('NTESSTUDYSI'),
        'c0-scriptName': 'CourseBean',
        'c0-methodName': 'getLessonUnitLearnVo',
        'c0-id': '0',
        'c0-param0': 'number:{}'.format(content_id),
        'c0-param1': 'number:{}'.format(file_type_number),
        'c0-param2': 'number:0',
        'c0-param3': 'number:{}'.format(file_id),
        'batchId': '1506405047240'
    }
    custom_header = {
        'Accept': '*/*',
        'Content-Type': 'text/plain',
    }
    resp = retry_request(QUERY_FILE_URL, data=data, headers=custom_header)
    if file_type == 'video':
        video_match = VIDEO_UEL_PTN.findall(resp.text)
        if video_match:
            video_dict = dict(video_match)
            for resolution_key in RESOLUTION_TYPES:
                if resolution_key in video_dict:
                    return video_dict.get(resolution_key)
    else:
        doc_match = DOC_URL_PTN.findall(resp.text)
        if doc_match:
            return doc_match[0]


def reindex_file_name(term):
    """格式化lesson名称"""
    new_term = OrderedDict()
    week_index_counter = 1
    for week_name, week_value in term.items():
        new_term[week_name] = OrderedDict()
        lesson_index_counter = 1  # 重新索引lesson
        for lesson_name, lesson_value in week_value.items():
            new_term[week_name][lesson_name] = OrderedDict()
            video_index_counter = 1  # 重新索引视频
            doc_index_counter = 1  # 重新索引课件
            for lecture_name, lecture_url in lesson_value.items():
                if '视频' in lecture_name or '课件' in lecture_name:
                    lecture_name = lesson_name
                if lecture_name.endswith('.mp4') or lecture_name.endswith('.flv'):
                    lecture_index_counter = video_index_counter
                else:
                    lecture_index_counter = doc_index_counter
                lecture_name = PREFIX_LECTURE_INDEX_PTN.sub('', lecture_name)
                file_name = '{}.{}.{}_{}'.format(week_index_counter, lesson_index_counter, lecture_index_counter,
                                                 lecture_name)
                new_term[week_name][lesson_name][file_name] = lecture_url
                lecture_index_counter += 1
                doc_index_counter += 1
            lesson_index_counter += 1
        week_index_counter += 1
    return new_term


def replace_url_host(original_url):
    """`v.stu.126.net`有时候会无法使用

    """
    o = 'http://v.stu.126.net/mooc-video'
    n = 'http://jdvodrvfb210d.vod.126.net/jdvodrvfb210d'
    return original_url.replace(o, n) if o in original_url else original_url


def download_file(term, output_folder):
    failure_list = []
    success_count = 0
    for week_name, lessons in term.items():
        week_path = os.path.join(output_folder, week_name)
        if not os.path.exists(week_path):
            os.mkdir(week_path)
        for lesson_name, files in lessons.items():
            if len(files) == 0:  # 排除`讨论`,`实验`等没有文件的lesson
                continue
            lesson_path = os.path.join(week_path, lesson_name)
            if not os.path.exists(lesson_path):
                os.mkdir(lesson_path)
            for file_name, file_url in files.items():
                if not file_url:
                    continue
                logger.info('[downloading] %s ---> %s', file_name, lesson_path)
                full_file_path = os.path.join(lesson_path, file_name)
                try:
                    resume_download_file(sess, file_url, full_file_path)
                    success_count += 1
                except Exception as e:
                    logger.warning('下载失败，下载链接：{}'.format(file_url))
                    failure_list.append((replace_url_host(file_url), full_file_path))

    retries = 3
    curr_retry = 1
    while curr_retry < retries:
        for file_url, full_file_path in failure_list:
            try:
                logger.info('第{}次重试，文件：{}'.format(curr_retry, full_file_path))
                resume_download_file(sess, file_url, full_file_path)
            except Exception as e:
                logger.warning('第{}次重试失败，下载链接：{}'.format(curr_retry, file_url))
                continue
            failure_list.remove((file_url, full_file_path))
            success_count += 1
        if len(failure_list) == 0:
            break
    logger.info('下载完成, 成功：{}个, 失败:{}'.format(success_count, len(failure_list)))


def get_output_course_folder(output, course_name, university_name):
    """获取课程文件保存目录"""
    export_folder = os.path.join(output, '{}_{}'.format(course_name, university_name))
    if not os.path.exists(export_folder):
        os.makedirs(export_folder)
    return export_folder


def export_catalog(term, output_folder):
    """输出课程目录到文本文件中"""
    separator = '    '
    file_path = os.path.join(output_folder, CATALOG_FNAME)
    with open(file_path, 'w', encoding='utf-8') as f:
        for week_name, week_value in term.items():
            f.write('{}\n'.format(week_name.strip()))
            for lesson_name, lesson_value in week_value.items():
                f.write('{}{}\n'.format(separator, lesson_name))


def get_download_urls(tid, doc_only=False):
    """获取下载链接

    Args:
        tid: 开课id
        doc_only: 是否之下载课件
    """
    data = {
        'callCount': '1',
        'scriptSessionId': '${scriptSessionId}190',
        'httpSessionId': sess.cookies.get('NTESSTUDYSI', 'b427803d95384cf496d3240af2526a60'),
        'c0-scriptName': 'CourseBean',
        'c0-methodName': 'getLastLearnedMocTermDto',
        'c0-id': '0',
        'c0-param0': 'number:{}'.format(tid),
        'batchId': '1506485521617'
    }
    custom_header = {
        'Accept': '*/*',
        'Content-Type': 'text/plain',
    }
    try:
        response = retry_request(COURSE_DETAIL_URL, data=data, headers=custom_header, timeout=20)
        if not response.ok:
            raise RequestExcetpion('获取视频链接响应状态码错误, 状态码：{}'.format(response.status_code))
    except Exception as e:
        raise RequestExcetpion('获取视频链接HTTP请求错误, {}'.format(e))

    # 解析响应数据
    # 其中，每行可能代表下面某种数据类型。每个lecture可能是视频，也可能是文档
    # |--week1
    #     |--lesson1.1
    #           |--lecture1.1.1
    #           |--lecture1.1.2
    #     |--lesson1.2

    term = OrderedDict()
    last_week_name = ''
    last_lesson_name = ''

    if response.ok:
        for line in response.content.splitlines():
            line = line.decode('unicode_escape')

            # 解析week
            week_match = week_ptn.findall(line)
            if week_match:
                last_week_name = clean_filename(week_match[0])
                term[last_week_name] = OrderedDict()
                logger.info(last_week_name)
                continue

            # 解析lesson
            lesson_match = lesson_ptn.findall(line)
            if lesson_match and last_week_name in term:
                last_lesson_name = clean_filename(lesson_match[0])
                term[last_week_name][last_lesson_name] = OrderedDict()
                logger.info('    %s', last_lesson_name)
                continue

            # 解析视频
            if not doc_only:
                # 获取视频链接
                video_match = video_ptn.findall(line)
                if video_match and last_lesson_name in term[last_week_name]:
                    content_id, _id, lecture_name, term_id = video_match[0]
                    lecture_name = clean_filename(lecture_name)
                    file_url = get_video_doc_url(content_id, _id)
                    postfix = 'mp4' if 'mp4' in file_url else 'flv'
                    term[last_week_name][last_lesson_name]['{}.{}'.format(lecture_name, postfix)] = file_url
                    logger.info('        %s', '{}.{}'.format(lecture_name, postfix))

            # 解析文档
            doc_match = doc_ptn.findall(line)
            if doc_match and last_lesson_name in term[last_week_name]:
                content_id, _id, lecture_name, term_id = doc_match[0]
                lecture_name = clean_filename(lecture_name)
                file_url = get_video_doc_url(content_id, _id, file_type='doc')
                postfix = 'doc' if '.doc' in file_url else 'pdf'
                term[last_week_name][last_lesson_name]['{}.{}'.format(lecture_name, postfix)] = file_url
                logger.info('        %s', '{}.{}'.format(lecture_name, postfix))

        if last_week_name == '':
            raise ParseException('未找到每周课程名称列表')
        term = reindex_file_name(term)
        return term


def main(url, username, password, output, doc_only):
    login(username, password)
    course_id = get_course_id_from_url(url)
    course_info = get_course_base_info(course_id, url)
    term = None
    for tid in course_info['tids'][::-1]:
        try:
            term = get_download_urls(tid, doc_only=doc_only)
            break
        except ParseException:
            logger.warning('开课id：{}未发现视频资源，本次开课已经关闭'.format(tid))
    if term is None:
        raise ParseException('未找到视频资源，可能因为所有开课都已关闭')
    output_folder = get_output_course_folder(output, course_info['course_name'], course_info['university_name'])
    export_catalog(term, output_folder)
    download_file(term, output_folder)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--username',
                        default='535036628@qq.com',
                        dest='username',
                        type=str,
                        required=False,
                        help="爱课程用户名, 默认：535036628@qq.com")
    parser.add_argument('-p', '--passwd',
                        default='aikechengp',
                        dest='password',
                        type=str,
                        required=False,
                        help="爱课程密码, 默认：aikechengp")
    parser.add_argument('-o', '--output',
                        dest='output',
                        default='.',
                        type=str,
                        required=False,
                        help='文件下载路径，默认：当前路径')
    parser.add_argument("url", type=str, help="课程链接")
    parser.add_argument("--doc-only", action="store_true", dest='doc_only', help="是否仅下载课件，默认：False")
    result = parser.parse_args()
    main(result.url, result.username, result.password, result.output, result.doc_only)
