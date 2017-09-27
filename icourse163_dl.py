# -*- coding:utf-8 -*-
import os
import re
import time
import logging
import argparse

import requests
from utils import clean_filename
from utils import resume_download_file

from exceptions import LoginException
from exceptions import RequestExcetpion

try:
    import simplejson as json
except ImportError as e:
    import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

logger = logging.getLogger(__name__)

INDEX_URL = 'http://www.icourse163.org'
QUERY_FILE_URL = 'http://www.icourse163.org/dwr/call/plaincall/CourseBean.getLessonUnitLearnVo.dwr'
VIDEO_UEL_PTN = re.compile('(\w+)="(.+?)";s')
DOC_URL_PTN = re.compile('textOrigUrl:"(\S+?)",')
OUTPUT_FOLDER = './'
# 登陆
AKC_LOGIN_URL = 'http://www.icourse163.org/passport/reg/icourseLogin.do'
AKC_USERNAME = '535036628@qq.com'
AKC_PASSWD = 'aikechengp'

# 课程
COURSE_DETAIL_URL = 'http://www.icourse163.org/dwr/call/plaincall/CourseBean.getLastLearnedMocTermDto.dwr'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.78 Safari/537.36',
    'Referer': 'http://www.icourse163.org/',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
}
RESOLUTION_TYPES = {
    'shd': ['mp4ShdUrl', 'flvShdUrl'],
    'hd': ['mp4HdUrl', 'flvHdUrl'],
    'sd': ['mp4SdUrl', 'flvSdUrl']
}
DEFAULT_RESOLUTION = 'shd'

# video:     contentId       id          name        teremId
video_reg = re.compile(
    'contentId=(\d+);.+contentType=1;.+id=(\d+);.+name=\"(.+)\";.+?resourceInfo=null;s\d+.termId=(\d+);')
# doc(pdf):      contentId
doc_reg = re.compile(
    'contentId=(\d+);.+contentType=3;.+id=(\d+);.+name=\"(.+)\";.+?resourceInfo=null;s\d+.termId=(\d+);')
# lesson:       name
lesson_reg = re.compile('chapterId=.+?contentId=null.+?name="(.+?)";s.+?releaseTime=')
# week:      name
week_reg = re.compile('contentId=null;s.+?lessons.+?name="(.+?)";s.+?published=')

sess = requests.Session()
sess.headers = HEADERS


def retry_request(url, method='POST', data=None, params=None, retries=3, **kwargs):
    curr_retry = 0
    while curr_retry < retries:
        try:
            resp = sess.request(method=method, url=url, data=data, params=params, **kwargs)
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


def pre_login():
    """pre login for get NTESSTUDYSI Cookie"""
    resp = retry_request(INDEX_URL, method='GET', timeout=20)
    if not sess.cookies.get('NTESSTUDYSI'):
        raise RequestExcetpion('pre login error, `NTESSTUDYSI` not in cookies')


def login(username, passwd):
    """login icourse163 by aikecheng account"""
    pre_login()
    data = {
        'returnUrl': 'aHR0cDovL3d3dy5pY291cnNlMTYzLm9yZy8=',
        'failUrl': 'aHR0cDovL3d3dy5pY291cnNlMTYzLm9yZy9tZW1iZXIvbG9naW4uaHRtP2VtYWlsRW5jb2RlZD1OVE0xTURNMk5qSTRRSEZ4TG1OdmJRPT0=',
        'savelogin': 'false',
        'oauthType': '',
        'username': username,
        'passwd': passwd
    }
    try:
        resp = sess.post(AKC_LOGIN_URL, data=data, timeout=20)
    except Exception as e:
        raise LoginException('login request error:%s' % e)
    if username not in sess.cookies.get('STUDY_INFO'):
        raise LoginException('login request success, but login cookies not found')
    logger.info('login success...')


def get_course_detail(tid):
    """get course detail page, then parse this page content and get video/doc url"""
    data = {
        'callCount': '1',
        'scriptSessionId': '${scriptSessionId}190',
        'httpSessionId': sess.cookies.get('NTESSTUDYSI'),
        'c0-scriptName': 'CourseBean',
        'c0-methodName': 'getLastLearnedMocTermDto',
        'c0-id': '0',
        'c0-param0': 'number:{}'.format(tid),
        'batchId': '1506394059754'
    }
    custom_header = {
        'Accept': '*/*',
        'Content-Type': 'text/plain',
    }
    try:
        response = sess.post(COURSE_DETAIL_URL, data=data, headers=custom_header, timeout=20)
        if not response.ok:
            raise RequestExcetpion('get course detail error, %d' % response.status_code)
    except Exception as e:
        raise RequestExcetpion('get course detail error, %s' % e)
    return response


def get_file_url(content_id, _id, resolution=None, file_type='video'):
    """query video/doc url by contentId and id"""
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
        'c0-param3': 'number:{}'.format(_id),
        'batchId': '1506405047240'
    }
    custom_header = {
        'Accept': '*/*',
        'Content-Type': 'text/plain',
    }
    resp = retry_request(QUERY_FILE_URL, data=data, headers=custom_header, timeout=20)
    if file_type == 'video':
        match = VIDEO_UEL_PTN.findall(resp.text)
        if match:
            match_dict = dict(match)
            if resolution and resolution in RESOLUTION_TYPES:
                for v in RESOLUTION_TYPES.get(resolution):
                    if v in match_dict:
                        return match_dict.get(v)

            for key, values in RESOLUTION_TYPES.items():
                for v in values:
                    if v in match_dict:
                        return match_dict.get(v)
    elif file_type == 'doc':
        doc_match = DOC_URL_PTN.findall(resp.text)
        if doc_match:
            return doc_match[0]


def dump_course_detail(dict_result, file_path):
    """dump query result to local file"""
    json.dump(dict_result, open(file_path, 'w', encoding='utf-8'), encoding='utf-8')


def parse_course_detail(content, output_folder, tid, resolution):
    """parse course video and doc detail from response body or xxx.json file"""
    json_file_path = os.path.join(output_folder, '{}.json'.format(tid))
    if os.path.exists(json_file_path):
        return json.load(open(json_file_path, 'r', encoding='utf-8'))

    term = dict()
    last_week_name = ''
    last_lesson_name = ''

    for line in content.splitlines():
        line = line.decode('unicode_escape')
        week_match = week_reg.findall(line)
        if week_match:
            last_week_name = clean_filename(week_match[0])
            term[last_week_name] = dict()
            logger.info(last_week_name)
            continue

        lesson_match = lesson_reg.findall(line)
        if lesson_match and last_week_name in term:
            last_lesson_name = clean_filename(lesson_match[0])
            term[last_week_name][last_lesson_name] = list()
            logger.info('    %s', last_lesson_name)
            continue

        video_match = video_reg.findall(line)
        if video_match and last_lesson_name in term[last_week_name]:
            content_id, _id, lecture_name, term_id = video_match[0]
            file_url = get_file_url(content_id, _id, resolution=resolution)
            postfix = 'mp4' if 'mp4' in file_url else 'flv'
            term[last_week_name][last_lesson_name].append(('{}.{}'.format(lecture_name, postfix), file_url))
            logger.info('        %s', '{}.{}'.format(lecture_name, postfix))

        doc_match = doc_reg.findall(line)
        if doc_match and last_lesson_name in term[last_week_name]:
            content_id, _id, lecture_name, term_id = doc_match[0]
            file_url = get_file_url(content_id, _id, file_type='doc')
            postfix = 'doc' if '.doc' in file_url else 'pdf'
            term[last_week_name][last_lesson_name].append(('{}.{}'.format(lecture_name, postfix), file_url))
            logger.info('        %s', '{}.{}'.format(lecture_name, postfix))
    dump_course_detail(term, json_file_path)
    return term


def download_file(term, output_folder):
    failure_list = []

    for week_name, lessons in term.items():
        week_path = os.path.join(output_folder, week_name)
        if not os.path.exists(week_path):
            os.mkdir(week_path)
        for lesson_name, files in lessons.items():
            lesson_path = os.path.join(week_path, lesson_name)
            if len(files) == 0:  # 排除`讨论`,`实验`等没有文件的lesson
                continue
            if not os.path.exists(lesson_path):
                os.mkdir(lesson_path)
            for file_name, file_url in files:
                if not file_url:
                    continue
                logger.info('[downloading] %s ---> %s', file_name, lesson_path)
                full_file_path = os.path.join(lesson_path, file_name)
                try:
                    resume_download_file(sess, file_url, full_file_path)
                except Exception as e:
                    logger.warning('download %s fail', file_name)
                    failure_list.append((file_url, full_file_path))

    retries = 3
    curr_retry = 0
    while curr_retry < retries:
        for file_url, full_file_path in failure_list:
            try:
                resume_download_file(sess, file_url, full_file_path)
            except:
                continue
            failure_list.remove((file_url, full_file_path))
        if len(failure_list) == 0:
            break
    logger.info('download complete, fail %d', len(failure_list))


def main(course, username, passwd, output, resolution):
    # 1.登陆
    login(username, passwd)
    m = re.compile('(\S+?)\?tid=(\d+)').findall(course)
    if not m:
        logger.warning('course parameter is illegal')
        raise ValueError
    course_name, tid = m[0]
    output_folder = os.path.join(output, course_name)
    if not os.path.exists(output_folder):
        os.mkdir(output_folder)
    # 2.获取该门课的详情页
    resp = get_course_detail(tid)
    # 3.解析课程详情页，获取资源的详细地址
    term = parse_course_detail(resp.content, output_folder, tid, resolution)
    # 4.下载所有资源
    download_file(term, output_folder)


if __name__ == '__main__':
    parse = argparse.ArgumentParser()

    parse.add_argument('-u', '--username',
                       default=AKC_USERNAME,
                       dest='username',
                       type=str,
                       required=False,
                       help="第三方登陆网站爱课程的用户名, 默认:535036628@qq.com")
    parse.add_argument('-p', '--passwd',
                       default=AKC_PASSWD,
                       dest='passwd',
                       type=str,
                       required=False,
                       help="第三方登陆网站爱课程的密码, 默认:aikechengp")
    parse.add_argument('-c', '--course',
                       dest='course',
                       type=str,
                       required=True,
                       help='链接中的课程信息，如:TONGJI-47017?tid=44002')

    parse.add_argument('-o', '--output',
                       dest='output',
                       default=OUTPUT_FOLDER,
                       type=str,
                       required=False,
                       help='文件下载路径，默认：当前路径')

    parse.add_argument('-r', '--resolution',
                       dest='resolution',
                       default=DEFAULT_RESOLUTION,
                       type=str,
                       choices=['shd', 'hd', 'sd'],
                       required=False,
                       help='视频清晰度，shd:超清, hd:高清, sd:标清, 默认:shd')
    result = parse.parse_args()
    main(result.course, result.username, result.passwd, result.output, result.resolution)
