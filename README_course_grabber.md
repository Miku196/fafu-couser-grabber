# 老版正方教务系统抢课脚本

> 🎯 一个高效、安全、可配置的老版正方教务系统自动抢课工具

## ✨ 特性

- 🔧 **高度可配置** - JSON配置文件，轻松设置课程和参数
- 📝 **详细日志** - 实时记录抢课过程，支持文件和控制台输出
- 🚀 **多线程支持** - 可同时抢多门课程（可选）
- ⚡ **智能重试** - 自动处理网络异常和服务器错误
- 🛡️ **安全防ban** - 可调节请求间隔，避免被系统封禁
- 📊 **状态监控** - 实时显示抢课进度和结果

## 📋 系统要求

- Python 3.6+
- requests 库
- 老版正方教务系统（URL包含 `default2.aspx`）

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install requests ddddocr beautifulsoup4
```

### 2. 下载脚本

```bash
git clone https://github.com/your-username/course-grabber.git
cd course-grabber
```

### 3. 首次运行

```bash
python course_grabber.py
```

脚本会自动创建 `course_config.json` 配置文件。

### 4. 配置课程信息

编辑 `course_config.json` 文件：

```json
{
  "base_url": "http://jwgl.fafu.edu.cn/(xxxxx)/default2.aspx",
  "login_url": "http://jwgl.fafu.edu.cn/(xxxxx)/default2.aspx", 
  "select_url": "http://jwgl.fafu.edu.cn/(xxxxx)/xsxk.aspx",
  "student_id": "你的学号",
  "password": "你的密码",
  "courses": [
    {
      "name": "高等数学A",
      "course_id": "MATH001",
      "class_id": "001",
      "teacher": "张教授",
      "enabled": true
    }
  ],
  "settings": {
    "max_attempts": 1000,
    "interval": 0.5,
    "timeout": 10,
    "enable_threading": false
  }
}
```

### 5. 开始抢课

```bash
python course_grabber.py
```

## ⚙️ 配置说明

### 基本设置

| 参数 | 说明 | 示例 |
|------|------|------|
| `base_url` | 教务系统主页地址 | `http://jwgl.xxx.edu.cn/(xxx)/default2.aspx` |
| `login_url` | 登录页面地址 | 通常与 `base_url` 相同 |
| `select_url` | 选课页面地址 | `http://jwgl.xxx.edu.cn/(xxx)/xsxk.aspx` |
| `student_id` | 学号 | `2021001001` |
| `password` | 密码 | `your_password` |

### 课程设置

每门课程包含以下字段：

| 参数 | 说明 | 必填 | 示例 |
|------|------|------|------|
| `name` | 课程名称（用于显示） | 是 | "高等数学A" |
| `course_id` | 课程号 | 是 | "MATH001" |
| `priority` | 课程优先级(数字越小优先级越高) | 否 | 1 |
| `classes` | 教学班列表 | 是 | - |

每个教学班包含以下字段：

| 参数 | 说明 | 必填 | 示例 |
|------|------|------|------|
| `class_id` | 教学班号 | 是 | "001" |
| `teacher` | 任课教师 | 否 | "张教授" |
| `enabled` | 是否启用抢课 | 否 | true |
| `priority` | 教学班优先级 | 否 | 1 |
| `backup` | 是否为备用教学班 | 否 | false |
| `schedule` | 上课时间 | 否 | {"week":"1-16","day":"1","time":"1-2"} |

### 高级设置

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `max_attempts` | 最大尝试次数 | 1000 |
| `interval` | 请求间隔（秒） | 0.5 |
| `timeout` | 请求超时（秒） | 10 |
| `retry_delay` | 重试延迟时间（秒） | 1.0 |
| `enable_threading` | 是否启用多线程 | false |
| `thread_count` | 线程数量 | 3 |
| `validation_code_retry` | 验证码重试次数 | 3 |
| `enable_priority` | 是否启用优先级抢课 | true |
| `enable_backup_classes` | 是否启用备用教学班 | true |

## 🔍 如何获取课程参数

1. **登录教务系统**，进入选课页面
2. **打开浏览器开发者工具**（F12）
3. **切换到 Network 标签页**
4. **尝试选择一门课程**
5. **查看 POST 请求**，找到选课相关的请求
6. **复制请求参数**中的课程号、教学班号等信息

## 📊 日志说明

脚本运行时会产生两种日志：

- **控制台输出** - 实时显示关键信息
- **文件日志** - `course_grabber.log` 包含详细记录

日志级别说明：
- `INFO` - 重要信息（登录成功、抢课成功等）
- `WARNING` - 警告信息（时间冲突等）
- `ERROR` - 错误信息（登录失败、网络异常等）
- `DEBUG` - 调试信息（每次尝试的详细结果）

## ⚠️ 注意事项

1. **请求频率** - 建议 `interval` 设置为 0.5 秒以上，避免被系统封禁
2. **账号安全** - 不要在公共场所运行，保护好账号密码
3. **网络环境** - 建议在校园网环境下使用
4. **合理使用** - 请遵守学校相关规定，不要恶意抢课

## 🛠️ 故障排除

### 登录失败
- 检查学号密码是否正确
- 确认教务系统 URL 是否正确
- 查看是否需要验证码（暂不支持）

### 抢课失败
- 确认课程号、教学班号是否正确
- 检查是否在选课时间内
- 查看日志了解具体失败原因

### 网络异常
- 检查网络连接
- 尝试增加 `timeout` 值
- 减少 `interval` 值

## 📄 开源协议

本项目采用 [MIT License](LICENSE) 开源协议。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## ⭐ 支持

如果这个项目对你有帮助，请给个 Star ⭐

---

**免责声明**: 本工具仅供学习交流使用，请遵守学校相关规定，不要用于任何违规行为。 