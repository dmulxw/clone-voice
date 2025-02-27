import locale
import os
import queue
import sys
import threading

import torch
from dotenv import load_dotenv

load_dotenv()
ROOT_DIR = os.getcwd()  # os.path.dirname(os.path.abspath(__file__))
os.environ['TTS_HOME'] = ROOT_DIR

print(f"DIR: {ROOT_DIR}")
LANG = "en" if locale.getdefaultlocale()[0].split('_')[0].lower() != 'zh' else "zh"

if sys.platform == 'win32':
    os.environ['PATH'] = f'{ROOT_DIR};{ROOT_DIR}\\ffmpeg;' + os.environ['PATH']
else:
    os.environ['PATH'] = f'{ROOT_DIR}:{ROOT_DIR}/ffmpeg:' +  os.environ['PATH']


def setorget_proxy():
    proxy = os.environ.get("http_proxy", '') or os.environ.get("HTTP_PROXY", '')
    if proxy:
        os.environ['AIOHTTP_PROXY'] = "http://" + proxy.replace('http://', '')
        os.environ['HTTPS_PROXY'] = "http://" + proxy.replace('http://', '')
        return proxy
    return None


# 存放录制好的素材，5-15s的语音 wav
VOICE_DIR = os.path.join(ROOT_DIR, 'static/voicelist')
# 存放经过tts转录后的wav文件
TTS_DIR = os.path.join(ROOT_DIR, 'static/ttslist')
# 临时目录
TMP_DIR = os.path.join(ROOT_DIR, 'static/tmp')
# 声音转声音 模型是否存在
if os.path.exists(os.path.join(ROOT_DIR, "tts/voice_conversion_models--multilingual--vctk--freevc24/model.pth")):
    VOICE_MODEL_EXITS = True
else:
    VOICE_MODEL_EXITS = False

if os.path.exists(os.path.join(ROOT_DIR, "tts/tts_models--multilingual--multi-dataset--xtts_v2/model.pth")):
    TEXT_MODEL_EXITS = True
else:
    TEXT_MODEL_EXITS = False

if not os.path.exists(VOICE_DIR):
    os.makedirs(VOICE_DIR)
if not os.path.exists(TTS_DIR):
    os.makedirs(TTS_DIR)
if not os.path.exists(TMP_DIR):
    os.makedirs(TMP_DIR)

device = "cuda" if torch.cuda.is_available() else "cpu"
q = queue.Queue(maxsize=100)
q_sts = queue.Queue(maxsize=100)
global_tts_result = {}
global_sts_result = {}
# 用于通知线程退出的事件
exit_event = threading.Event()
tts_n = 0
sts_n = 0

download_address = 'https://github.com/jianchang512/clone-voice/releases/tag/v0.0.1'

langdict = {
    "zh": {
        "lang1": "\n=====源码部署须知======\n如果你是源码部署，需要先执行 python code_dev.py 文件，以便同意coqou-ai的授权协议(显示同意协议后输入 y )，然后从下载或更新模型，需要提前配置好全局vpn\n=====\n",
        "lang2": "准备启动 【文字->声音】 线程",
        "lang3": "不存在 【文字->声音】 模型，下载地址",
        "lang4": "准备启动 【声音->声音】 线程",
        "lang5": "不存在 【声音->声音】 模型，下载地址",
        "lang6": "不存在任何模型，请先下载模型后，解压到tts目录下",
        "lang7": "启动后加载模型可能需要几分钟,请耐心等待浏览器自动打开",
        "lang8": "[已打开浏览器窗口,如果未能自动打开，你也可以手动打开地址]",
        "lang9": "启动 声音->声音 线程失败",
        "lang10": "启动 声音->声音 线程成功",
        "lang11": "代理不可用，请设置正确的代理，以便下载模型",
        "lang12": "请在该文件中正确设置 http 代理，以便能下载模型",
        "lang13": "启动 文字->声音 线程失败",
        "lang14": "启动 文字->声音 线程成功",
        "lang15":"[文字->声音]线程还没有启动完毕，若模型已存在，请等待，否则请下载模型. ", 
        "lang16":"[声音->声音]线程还没有启动完毕，若模型已存在，请等待，否则请下载模型"
    },
    "en": {
        "lang1": "\n=====Source Code Deployment Notes======\nIf you are deploying from source code, you need to execute the python code_dev.py file first to agree to the coqou-ai license agreement (display agreement and enter y), and then download or update the model. You need to configure the global VPN in advance\n=====\n",
        "lang2": "Preparing to start the [Text -> Speech] thread",
        "lang3": "No [Text -> Speech] model exists, download address",
        "lang4": "Preparing to start the [Speech -> Speech] thread",
        "lang5": "No [Speech -> Speech] model exists, download address",
        "lang6": "No models exist, please download the models first and unzip them to the tts directory",
        "lang7": "It may take a few minutes to load the model after starting, please be patient and wait for the browser to open automatically",
        "lang8": "[Browser window opened. If it does not open automatically, you can also open the address manually]",
        "lang9": "Failed to start the [Speech -> Speech] thread",
        "lang10": "Successfully started the [Speech -> Speech] thread",
        "lang11": "Proxy unavailable, please set the correct proxy to download the model",
        "lang12": "Please set the http proxy correctly in this file to download the model",
        "lang13": "Failed to start the [Text -> Speech] thread",
        "lang14": "Successfully started the [Text -> Speech] thread", 
        "lang15":"[text->speech]not start，if model has downloaded，please wait a moment，else download. ", 
        "lang16":"[speech->speech]not start，if model has downloaded，please wait a moment，else download"
    }
}
langlist = langdict[LANG]

updatetips=""