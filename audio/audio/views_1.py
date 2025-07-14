from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators import csrf
from django.shortcuts import render
import websocket
import websockets
import pyaudio
import cv2
import time
import threading
import os
import pdfplumber
import asyncio

# 全局变量用于控制视频流
is_streaming = False
streaming_thread = None

HOST = '10.110.147.177'  # 服务器IP
PORT_audio = 8000
PORT_video = 8765
PORT_text = 8020
WS_audio_URL = f"ws://{HOST}:{PORT_audio}/ws/audio" 
WS_video_URL = f"ws://{HOST}:{PORT_video}/ws/video" 
WS_text_URL = f"ws://{HOST}:{PORT_text}/ws/text" 
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

FORMAT = pyaudio.paInt16
TTS_URI = "ws://10.110.147.177:8050"

import threading
import time

# 全局标志位 + 录音线程
is_recording = False
recording_thread = None


"""
websocket通信
"""
"""
语音传输
"""
def audio_recording():
    global is_recording

    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    try:
        ws = websocket.create_connection(WS_audio_URL)
        print("WebSocket 连接成功，开始发送音频数据...")

        try:
            while is_recording:
                data = stream.read(CHUNK)
                ws.send(data, opcode=websocket.ABNF.OPCODE_BINARY)  # 用 binary 发送音频流
        finally:
            ws.close()
            print("WebSocket 连接已关闭")

    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()
        print("录音已停止，资源已释放")

def audio(request):
    global is_recording, recording_thread
    ctx = {}

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'start' and not is_recording:
            is_recording = True
            recording_thread = threading.Thread(target=audio_recording)
            recording_thread.start()
            ctx['rlt'] = '正在录音'
        elif action == 'stop' and is_recording:
            is_recording = False
            recording_thread.join()
            ctx['rlt'] = '录音停止。'
        # else:
        #     ctx['rlt'] = '无效操作或状态不变。'

    return render(request, "audio.html", ctx)

"""
视频传输
"""

def video_streaming():
    global is_streaming
    
    cap = cv2.VideoCapture(0)  # 默认摄像头
    
    try:
        # 连接 WebSocket 服务器
        # ws = websocket.create_connection("ws://localhost:8765")
        ws = websocket.create_connection(WS_video_URL)
        print("WebSocket 连接成功，开始发送视频数据...")
        
        try:
            while is_streaming and cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                # 编码为 JPEG 格式
                ret, buffer = cv2.imencode('.jpg', frame)
                if not ret:
                    continue
                
                # 发送图像帧（二进制）
                ws.send(buffer.tobytes(), opcode=websocket.ABNF.OPCODE_BINARY)
                
                # 控制帧率 (30fps)
                time.sleep(1/30)
        
        finally:
            # 发送结束标志
            try:
                ws.send("EOF")
                print("已发送结束标志")
            except:
                print("发送结束标志失败")
            ws.close()
            print("WebSocket 连接已关闭")
    
    finally:
        cap.release()
        print("摄像头已释放")

def video(request):
    global is_streaming, streaming_thread
    context = {'is_streaming': is_streaming}
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'start' and not is_streaming:
            # 开始视频流
            is_streaming = True
            streaming_thread = threading.Thread(target=video_streaming)
            streaming_thread.start()
            context['status'] = "视频流传输中..."
            context['is_streaming'] = True
        
        elif action == 'stop' and is_streaming:
            # 停止视频流
            is_streaming = False
            if streaming_thread is not None:
                streaming_thread.join()
            context['status'] = "视频流已停止"
            context['is_streaming'] = False
    
    return render(request, "audio.html", context)


"""
解析pdf并传输
"""

def text_trans(text):
    ws = websocket.create_connection(WS_text_URL)
    ws.send(text)
    print("简历发送成功")


def ai_interview_page(request):
    pdf_message = None
    if request.method == 'POST' and request.FILES.get('pdf_file'):
        pdf_file = request.FILES['pdf_file']
        basedir = os.path.join('media', 'uploads')
        upload_path = os.path.join(basedir, pdf_file.name)
        os.makedirs(os.path.dirname(upload_path), exist_ok=True)
        with open(upload_path, 'wb+') as f:
            for chunk in pdf_file.chunks(): 
                f.write(chunk)
        pdf_message = f"上传成功：{pdf_file.name}"
    with pdfplumber.open(upload_path) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text()
    text_trans(text)
    return render(request, 'audio.html', {
        'rlt': '未开始',
        'status': '未连接',
        'pdf_message': pdf_message,
    })


"""
开始页面同时打开tts回传服务
"""

# 音频播放协程
async def receive_and_play_audio(TTS_URI):

    p = pyaudio.PyAudio()
    try:
        async with websockets.connect(TTS_URI, open_timeout=120) as ws:
            print("✅ 已连接服务器，等待音频...")
            while True:
                stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True)

                while True:
                    message = await ws.recv()

                    if isinstance(message, str) and message == "EOF":
                        print("🎧 播放完成")
                        break
                    elif isinstance(message, bytes):
                        stream.write(message)

                stream.stop_stream()
                stream.close()
    except Exception as e:
        print("播放出错:", e)
    finally:
        p.terminate()

def start_audio_playback():
    asyncio.run(receive_and_play_audio(TTS_URI))

# 视图函数
def start(request):
    if request.method == "POST":
        threading.Thread(target=start_audio_playback, daemon=True).start()
        print('done')
        return render(request, 'audio.html')  # 或重定向到别的页面
    return render(request, 'start.html')  # 初始 GET 请求时展示按钮页


    

