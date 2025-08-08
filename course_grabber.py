#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
老版正方教务系统抢课脚本
适用于 default2.aspx 类型的正方教务系统
作者: FAFU Helper
开源许可: MIT License
"""

import requests
import time
import json
import logging
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional
import sys
import ddddocr
import io
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import time
from collections import defaultdict

class StatusMonitor:
    """实时状态监控类"""
    
    def __init__(self):
        self.status_data = defaultdict(dict)
        self.start_time = time.time()
        
    def update_status(self, course_name: str, status: str, details: str = ""):
        """更新课程状态"""
        self.status_data[course_name] = {
            'status': status,
            'details': details,
            'timestamp': time.time()
        }
        
    def get_status(self, course_name: str = None):
        """获取状态信息"""
        if course_name:
            return self.status_data.get(course_name, {})
        return dict(self.status_data)
        
    def get_runtime(self):
        """获取运行时间"""
        return time.time() - self.start_time

class NotificationManager:
    """通知管理类"""
    
    def __init__(self, config: Dict, logger: logging.Logger):
        self.config = config
        self.logger = logger
        
    def send_email(self, subject: str, content: str) -> bool:
        """发送邮件通知"""
        if not self.config['notifications']['email']['enabled']:
            return False
            
        try:
            msg = MIMEText(content, 'html', 'utf-8')
            msg['Subject'] = Header(subject, 'utf-8')
            msg['From'] = self.config['notifications']['email']['sender']
            msg['To'] = self.config['notifications']['email']['receiver']
            
            with smtplib.SMTP(
                self.config['notifications']['email']['smtp_server'],
                self.config['notifications']['email']['smtp_port']
            ) as server:
                server.starttls()
                server.login(
                    self.config['notifications']['email']['sender'],
                    self.config['notifications']['email']['password']
                )
                server.send_message(msg)
                
            self.logger.info("邮件通知发送成功")
            return True
        except Exception as e:
            self.logger.error(f"邮件发送失败: {e}")
            return False
            
    def send_wechat(self, title: str, content: str) -> bool:
        """发送Server酱微信通知"""
        if not self.config['notifications']['wechat']['enabled']:
            return False
            
        try:
            url = f"https://sctapi.ftqq.com/{self.config['notifications']['wechat']['serverchan_key']}.send"
            data = {
                "title": title,
                "desp": content
            }
            response = requests.post(url, data=data, timeout=10)
            if response.json().get('code') == 0:
                self.logger.info("微信通知发送成功")
                return True
            self.logger.error(f"微信通知发送失败: {response.text}")
            return False
        except Exception as e:
            self.logger.error(f"微信通知异常: {e}")
            return False

class CourseGrabber:
    """正方教务系统抢课器"""
    
    def __init__(self, config_file: str = "course_config.json"):
        """
        初始化抢课器
        
        Args:
            config_file: 配置文件路径
        """
        self.config = self.load_config(config_file)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.last_active = time.time()
        self.logger = self.setup_logger()
        self.is_running = False
        self.ocr = ddddocr.DdddOcr(show_ad=False)  # 初始化OCR
        self.notifier = NotificationManager(self.config, self.logger)
        self.monitor = StatusMonitor()
        
    def load_config(self, config_file: str) -> Dict:
        """加载配置文件"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            self.create_default_config(config_file)
            print(f"已创建默认配置文件 {config_file}，请填写后重新运行")
            sys.exit(1)
    
    def create_default_config(self, config_file: str):
        """创建默认配置文件"""
        default_config = {
            "base_url": "http://jwgl.example.edu.cn/(xxxxx)/default2.aspx",
            "login_url": "http://jwgl.example.edu.cn/(xxxxx)/default2.aspx",
            "select_url": "http://jwgl.example.edu.cn/(xxxxx)/xsxk.aspx",
            "student_id": "",
            "password": "",
            "courses": [
                {
                    "name": "课程名称示例",
                    "course_id": "课程号",
                    "classes": [
                        {
                            "class_id": "教学班号1",
                            "teacher": "教师姓名1",
                            "enabled": True,
                            "schedule": {
                                "week": "1-16",
                                "day": "1",
                                "time": "1-2"
                            }
                        },
                        {
                            "class_id": "教学班号2",
                            "teacher": "教师姓名2",
                            "enabled": True,
                            "schedule": {
                                "week": "1-16",
                                "day": "2",
                                "time": "3-4"
                            }
                        }
                    ]
                }
            ],
            "settings": {
                "max_attempts": 1000,
                "interval": 0.5,
                "timeout": 10,
                "retry_delay": 1.0,
                "enable_threading": False,
                "thread_count": 3,
                "validation_code_retry": 3  # 验证码重试次数
            },
            "notifications": {
                "email": {
                    "enabled": False,
                    "smtp_server": "",
                    "smtp_port": 587,
                    "sender": "",
                    "password": "",
                    "receiver": ""
                },
                "wechat": {
                    "enabled": False,
                    "serverchan_key": ""
                }
            }
        }
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
    
    def setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger('CourseGrabber')
        logger.setLevel(logging.INFO)
        
        # 文件处理器
        file_handler = logging.FileHandler('course_grabber.log', encoding='utf-8')
        file_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter('%(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def login(self) -> bool:
        """
        登录教务系统
        
        Returns:
            bool: 登录是否成功
        """
        try:
            # 检查会话状态
            if time.time() - self.last_active > 1800:  # 30分钟无活动
                self.logger.info("会话超时，重新初始化")
                self.session = requests.Session()
            
            # 获取登录页面获取验证码和动态参数
            login_page = self.session.get(
                self.config['login_url'],
                timeout=self.config['settings']['timeout']
            )
            self.last_active = time.time()
            
            # 解析验证码和动态参数（需要根据实际页面调整）
            viewstate = self._parse_viewstate(login_page.text)
            validation_code = self._get_validation_code()
            
            login_data = {
                'TextBox1': self.config['student_id'],
                'TextBox2': self.config['password'],
                'RadioButtonList1': '学生',
                '__VIEWSTATE': viewstate,
                'txtSecretCode': validation_code,
                # 其他必要参数
            }
            
            response = self.session.post(
                self.config['login_url'],
                data=login_data,
                timeout=self.config['settings']['timeout']
            )
            
            if '学生个人中心' in response.text or '选课' in response.text:
                self.logger.info("登录成功")
                self.notifier.send_wechat(
                    "教务系统登录成功",
                    f"账号 {self.config['student_id']} 登录成功\n"
                    f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                return True
            elif '验证码错误' in response.text:
                self.logger.warning("验证码错误，将重试...")
                return False
            else:
                self.logger.error("登录失败，请检查账号密码")
                return False
                
        except Exception as e:
            self.logger.error(f"登录异常: {e}")
            return False
    
    def check_conflict(self, course1: Dict, course2: Dict) -> bool:
        """检查两门课程时间是否冲突"""
        if not all('schedule' in c for c in [course1, course2]):
            self.logger.debug(f"课程 {course1['name']} 或 {course2['name']} 缺少时间信息，跳过冲突检查")
            return False
            
        s1 = course1['schedule']
        s2 = course2['schedule']
        
        # 检查星期是否相同
        if s1['day'] != s2['day']:
            return False
            
        # 解析节次范围
        def parse_time(time_str):
            try:
                start, end = map(int, time_str.split('-'))
                return set(range(start, end+1))
            except:
                self.logger.warning(f"无效的时间格式: {time_str}")
                return set()
            
        time1 = parse_time(s1['time'])
        time2 = parse_time(s2['time'])
        
        if not time1 or not time2:
            return False
            
        # 检查节次是否有重叠
        conflict = not time1.isdisjoint(time2)
        if conflict:
            self.logger.info(f"⚠️ 检测到课程冲突: {course1['name']} 和 {course2['name']}")
            self.monitor.update_status(
                course1['name'],
                'conflict',
                f"与 {course2['name']} 时间冲突"
            )
        return conflict

    def grab_course(self, course: Dict, class_info: Optional[Dict] = None) -> bool:
        """
        抢指定课程
        
        Args:
            course: 课程信息字典
            class_info: 可选的教学班信息，如果为None则使用课程中的第一个教学班
            
        Returns:
            bool: 抢课是否成功
        """
        course_name = course['name']
        course_id = course['course_id']
        class_id = class_info['class_id'] if class_info else course['classes'][0]['class_id']
        
        select_data = {
            'kcxx': course_id,
            'jxbh': class_id,
            # 根据实际抓包结果添加其他必要参数
            '__EVENTTARGET': '',
            '__EVENTARGUMENT': '',
            # '__VIEWSTATE': '',  # 需要动态获取
        }
        
        try:
            response = self.session.post(
                self.config['select_url'],
                data=select_data,
                timeout=self.config['settings']['timeout']
            )
            
            response_text = response.text
            
            if '选课成功' in response_text or '已选' in response_text:
                self.monitor.update_status(
                    course_name,
                    'success',
                    f'课程号: {course_id} 教学班: {class_id}'
                )
                self.logger.info(f"✅ 抢课成功: {course_name}")
                self.notifier.send_wechat(
                    "抢课成功通知",
                    f"课程: {course_name}\n"
                    f"课程号: {course_id}\n"
                    f"教学班: {class_id}\n"
                    f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                return True
            elif '已满' in response_text or '选课人数已满' in response_text:
                self.monitor.update_status(
                    course_name,
                    'full',
                    '课程人数已满'
                )
                self.logger.debug(f"❌ 课程已满: {course_name}")
                return False
            elif '时间冲突' in response_text:
                self.monitor.update_status(
                    course_name,
                    'conflict',
                    '时间冲突'
                )
                self.logger.warning(f"⚠️ 时间冲突: {course_name}")
                return False
            else:
                self.logger.debug(f"⏳ 继续尝试: {course_name}")
                return False
                
        except Exception as e:
            self.logger.error(f"抢课异常 {course_name}: {e}")
            return False
    
    def grab_single_course(self, course: Dict):
        """
        单线程抢课(支持优先级和备用教学班)
        
        Args:
            course: 课程信息
        """
        course_name = course['name']
        max_attempts = self.config['settings']['max_attempts']
        interval = self.config['settings']['interval']
        enable_priority = self.config['settings'].get('enable_priority', False)
        enable_backup = self.config['settings'].get('enable_backup_classes', False)
        
        self.logger.info(f"开始抢课: {course_name}")
        
        # 获取所有教学班并按优先级排序
        classes = sorted(
            course.get('classes', [{}]),
            key=lambda x: x.get('priority', 1),
            reverse=not enable_priority
        )
        
        for attempt in range(1, max_attempts + 1):
            if not self.is_running:
                break
                
            # 尝试所有教学班(主选+备用)
            for class_info in classes:
                if not class_info.get('enabled', True):
                    continue
                    
                # 如果是备用班且未启用备用班功能则跳过
                if class_info.get('backup', False) and not enable_backup:
                    continue
                    
                if self.grab_course(course, class_info):
                    self.logger.info(f"🎉 {course_name} 抢课成功！教学班: {class_info['class_id']}")
                    self.notifier.send_wechat(
                        "抢课成功通知",
                        f"课程: {course_name}\n"
                        f"教学班: {class_info['class_id']}\n"
                        f"教师: {class_info.get('teacher', '')}\n"
                        f"尝试次数: {attempt}\n"
                        f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                    return
                
            if attempt % 100 == 0:
                self.logger.info(f"已尝试 {attempt} 次: {course_name}")
            
            time.sleep(interval)
        else:
            self.logger.warning(f"😞 {course_name} 抢课失败，已达最大尝试次数")
            self.notifier.send_email(
                "抢课失败通知",
                f"<h3>抢课失败通知</h3>"
                f"<p>课程名称: {course_name}</p>"
                f"<p>已达到最大尝试次数 {max_attempts} 次</p>"
                f"<p>时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>"
            )
    
    def start_grabbing(self):
        """开始抢课"""
        if not self.login():
            return
        
        self.is_running = True
        # 过滤已启用课程并检查冲突
        enabled_courses = []
        for course in self.config['courses']:
            if course.get('enabled', True):
                # 处理多教学班
                for class_info in course.get('classes', []):
                    if not class_info.get('enabled', True):
                        continue
                        
                    # 创建课程副本并添加教学班信息
                    course_copy = course.copy()
                    course_copy.update(class_info)
                    
                    # 检查与已选课程的冲突
                    conflict = any(
                        self.check_conflict(course_copy, selected)
                        for selected in enabled_courses
                        if 'schedule' in selected
                    )
                    if conflict:
                        self.logger.warning(f"⚠️ 课程 {course['name']} 教学班 {class_info['class_id']} 与其他课程时间冲突")
                        continue
                    enabled_courses.append(course_copy)
        
        if not enabled_courses:
            self.logger.warning("没有启用的课程")
            return
        
        self.logger.info(f"开始抢课，共 {len(enabled_courses)} 门课程")
        
        if self.config['settings'].get('enable_threading', False):
            # 优化后的多线程抢课
            from concurrent.futures import ThreadPoolExecutor, as_completed
            thread_count = self.config['settings'].get('thread_count', 3)
            success_count = 0
            
            with ThreadPoolExecutor(max_workers=thread_count) as executor:
                futures = {
                    executor.submit(self.grab_single_course, course): course
                    for course in enabled_courses
                }
                
                for future in as_completed(futures):
                    course = futures[future]
                    try:
                        if future.result():
                            success_count += 1
                            # 成功一个课程就停止其他线程
                            if self.config['settings'].get('stop_on_success', True):
                                executor.shutdown(wait=False)
                                break
                    except Exception as e:
                        self.logger.error(f"课程 {course['name']} 抢课线程异常: {str(e)}")
            
            self.logger.info(f"多线程抢课完成，成功 {success_count} 门课程")
        else:
            # 单线程抢课
            for course in enabled_courses:
                if not self.is_running:
                    break
                # 对于多教学班课程，每个教学班单独处理
                if 'classes' in course:
                    for class_info in course['classes']:
                        if not class_info.get('enabled', True):
                            continue
                        if not self.is_running:
                            break
                        self.grab_single_course({**course, **class_info})
                else:
                    self.grab_single_course(course)
        
        self.logger.info("抢课结束")
    
    def get_status_report(self) -> str:
        """获取状态报告"""
        report = []
        report.append(f"运行时间: {self.monitor.get_runtime():.1f}秒")
        report.append(f"当前状态: {'运行中' if self.is_running else '已停止'}")
        
        for course, data in self.monitor.get_status().items():
            status_map = {
                'success': '✅ 成功',
                'full': '❌ 已满',
                'conflict': '⚠️ 冲突',
                'error': '❗ 错误'
            }
            status = status_map.get(data['status'], data['status'])
            report.append(f"{course}: {status} - {data.get('details', '')}")
            
        return "\n".join(report)

    def stop_grabbing(self):
        """停止抢课"""
        self.is_running = False
        self.logger.info("正在停止抢课...")

def main():
    """主函数"""
    print("=== 老版正方教务系统抢课脚本 ===")
    print("作者: FAFU Helper")
    print("开源地址: https://github.com/your-username/course-grabber")
    print("=" * 40)
    
    grabber = CourseGrabber()
    
    try:
        grabber.start_grabbing()
        
        # 状态监控循环
        while grabber.is_running:
            print("\n当前状态:")
            print(grabber.get_status_report())
            print("=" * 40)
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n收到中断信号，正在停止...")
        grabber.stop_grabbing()
    except Exception as e:
        grabber.logger.error(f"程序异常: {e}")
        grabber.notifier.send_email(
            "抢课程序异常通知",
            f"<h3>抢课程序发生异常</h3>"
            f"<p>异常信息: {str(e)}</p>"
            f"<p>时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>"
            "<p>请检查程序运行状态</p>"
        )

    def _parse_viewstate(self, html: str) -> str:
        """从HTML中解析__VIEWSTATE值"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            viewstate = soup.find('input', {'name': '__VIEWSTATE'})
            if viewstate:
                return viewstate['value']
            self.logger.warning("未找到__VIEWSTATE，使用空值")
            return ""
        except Exception as e:
            self.logger.error(f"解析__VIEWSTATE失败: {e}")
            return ""
        
    def _get_validation_code(self) -> str:
        """获取验证码（带重试机制）"""
        max_retry = self.config['settings']['validation_code_retry']
        
        for attempt in range(1, max_retry + 1):
            try:
                # 下载验证码图片
                code_url = f"{self.config['base_url'].split('default2.aspx')[0]}CheckCode.aspx"
                response = self.session.get(
                    code_url,
                    timeout=self.config['settings']['timeout']
                )
                
                # 使用OCR识别
                img_bytes = io.BytesIO(response.content)
                code = self.ocr.classification(img_bytes.getvalue())
                
                # 验证码有效性检查
                if len(code) == 4 and code.isdigit():
                    self.logger.debug(f"验证码识别成功: {code}")
                    return code
                
                self.logger.warning(f"验证码识别可能错误: {code}")
                
            except Exception as e:
                self.logger.error(f"验证码识别失败(尝试{attempt}/{max_retry}): {e}")
                if attempt < max_retry:
                    time.sleep(1)
        
        self.logger.error(f"验证码识别达到最大重试次数 {max_retry}")
        return "0000"  # 默认值

if __name__ == "__main__":
    main()