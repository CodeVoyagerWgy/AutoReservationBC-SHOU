import requests
import json
import os
import ddddocr
import base64
from dotenv import load_dotenv, set_key

# 加载 .env 文件
load_dotenv()

# 全局常量
BASE_HEADERS = {
    'User-Agent': 'SWSuperApp/1.0.19 (iPad; iOS 18.0; Scale/2.00)'
}

# URL常量
LOGIN_URL = "https://uis.shou.edu.cn/token/password/passwordLogin"
QUERY_RESERVATION_URL = "https://meeting-reservation.shou.edu.cn/api/home/reserve4site"
CAPTCHA_URL_TEMPLATE = "https://meeting-reservation.shou.edu.cn/api/room/captcha/{}"
RESERVATION_URL = "https://meeting-reservation.shou.edu.cn/api/reservation"

# 登录函数
def login(username, password):
    login_data = {
        'appId': 'com.supwisdom.ahd',
        'clientId': 'CLIENT_ID',
        'deviceId': 'BBE18D7D-6696-4B4C-828B-348A116CD485',
        'mfaState': '9zT101',
        'osType': 'iOS',
        'password': password,
        'username': username
    }

    try:
        session = requests.session()
        response = session.post(LOGIN_URL, data=login_data, headers=BASE_HEADERS)
        response.raise_for_status()
        response_body = response.json()

        if response_body['code'] == 0:
            print("登录成功")
            return session, response_body['data']['idToken']
        else:
            print(f"登录失败: {response_body.get('message', '未知错误')}")
            return None, None
    except requests.RequestException as e:
        print(f"登录请求失败: {e}")
        return None, None
    except json.JSONDecodeError:
        print("无法解析登录响应")
        return None, None


# 查询预定函数
def query_reservation(session, token, date):
    query_headers = {**BASE_HEADERS, 'X-Id-Token': token}
    params = {'projectId': '1800403370013822977', 'date': date}

    try:
        response = session.get(QUERY_RESERVATION_URL, headers=query_headers, params=params)
        response.raise_for_status()
        print(response.text)
    except requests.RequestException as e:
        print(f"查询失败: {e}")


# 获取验证码函数
def get_captcha(session, token, room_id):
    captcha_url = CAPTCHA_URL_TEMPLATE.format(room_id)
    query_headers = {**BASE_HEADERS, 'X-Id-Token': token}

    try:
        response = session.get(captcha_url, headers=query_headers)
        response.raise_for_status()
        response_data = json.loads(response.text)

        if response_data['code'] == 200:
            return response_data['data']
        else:
            print(f"获取验证码错误: {response_data.get('msg', '未知错误')}")
            return ""
    except requests.RequestException as e:
        print(f"获取验证码失败: {e}")
        return ""


# OCR 识别验证码
def ocr_recognize(captcha_base64):
    ocr = ddddocr.DdddOcr()

    try:
        if captcha_base64.startswith('data:image'):
            captcha_base64 = captcha_base64.split(',')[1]
        image_data = base64.b64decode(captcha_base64)
        result = ocr.classification(image_data)
        print("OCR 识别结果:", result)
        return result
    except base64.binascii.Error as e:
        print(f"Base64 解码错误: {e}")
        return ""
    except Exception as e:
        print(f"OCR 识别错误: {e}")
        return ""


# 提交预约函数
def reserve(session, token, room_id, start_time, end_time, apply_date, retries=3):
    captcha_base64 = get_captcha(session, token, room_id)

    if not captcha_base64:
        print("验证码获取失败，停止预约")
        return

    for attempt in range(retries):
        capacha_code = ocr_recognize(captcha_base64)
        if not capacha_code:
            print("验证码识别失败，停止预约")
            return

        reservation_data = {
            "leaderName": "王贵友",
            "leaderId": "ec3906404af011ed6b031648282c5aa9",
            "captcha": capacha_code,
            "applyExtendList": [
                {
                    "endTime": end_time,
                    "applyDate": apply_date,
                    "beginTime": start_time
                }
            ],
            "subject": "羽毛球运动",
            "applicant": "100500",
            "roomId": room_id,
            "allowAgentRa": 0,
            "seatCount": 4,
            "phone": "17861006056",
            "leaderNo": "M220951640",
            "useRuleId": "1836673554756079618",
            "remark": "",
            "applicantLabel": "信息学院"
        }

        query_headers = {**BASE_HEADERS, 'X-Id-Token': token}

        try:
            response = session.post(RESERVATION_URL, json=reservation_data, headers=query_headers)
            response_data = response.json()
            print(response_data)

            if response_data['code'] == 200:
                print("预约成功")
                break
            elif response_data['code'] == 400 and response_data['msg'] == '验证码错误':
                print(f"验证码错误，第 {attempt + 1}/{retries} 次重试")
                captcha_base64 = get_captcha(session, token, room_id)
            else:
                print(f"预约失败: {response_data.get('message', '未知错误')}")
                break
        except requests.RequestException as e:
            print(f"预约请求失败: {e}")
            break


if __name__ == "__main__":
    # 从 .env 文件中加载用户名和密码
    username = os.getenv("USERNAME", "m220951640")
    password = os.getenv("PASSWORD", "wangguiyou123")
    token = os.getenv("TOKEN", None)  # 从 .env 文件读取 token

    room_id = '1805787236174073857'
    start_time = '18:00'
    end_time = '18:30'
    apply_date = '2024-10-16'

    session = requests.session()

    # 如果没有 token，则进行登录操作
    if not token:
        session, token = login(username, password)
        if token:
            # 登录成功后，将 token 写入 .env 文件
            set_key('.env', 'TOKEN', token)
    else:
        print("使用已有的 TOKEN 进行操作")

    if session and token:
        query_reservation(session, token, apply_date)
        reserve(session, token, room_id, start_time, end_time, apply_date)
