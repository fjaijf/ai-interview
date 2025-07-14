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
import json

# 全局变量用于控制视频流
is_streaming = False
streaming_thread = None

HOST = '10.110.147.177'  # 服务器IP
PORT_audio = 8000
PORT_video = 8765

WS_audio_URL = f"ws://{HOST}:{PORT_audio}/ws/audio" 
WS_video_URL = f"ws://{HOST}:{PORT_video}/ws/video" 

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

FORMAT = pyaudio.paInt16

ws = None
video_ws = None
import threading
import time

# 全局标志位 + 录音线程
is_recording = False
recording_thread = None


def connect_websocket_audio():
    global ws
    if ws is None:
        ws = websocket.create_connection(WS_audio_URL)
    print('连接成功')

def connect_websocket_video():
    global video_ws
    if video_ws is None:
        video_ws = websocket.create_connection(WS_video_URL)
    print('连接成功')

RETRY_LIMIT = 3   # 最大重试次数
RETRY_DELAY = 2   # 每次重试间隔时间（秒）



# def connect_websocket():
#     global ws
#     attempt = 0

#     while attempt < RETRY_LIMIT:
#         try:
#             if ws is None or not is_ws_connected(ws):
#                 print("正在尝试建立 WebSocket 连接...")
#                 ws = websocket.create_connection(
#                     WS_audio_URL,
#                     timeout=10,
#                     enable_multithread=True
#                 )
#                 start_heartbeat(ws)
#                 print("✅ WebSocket 连接成功")
#                 return True
#             else:
#                 print("🔁 已经存在有效连接")
#                 return True
#         except Exception as e:
#             print(f"❌ 连接失败: {e}")
#             attempt += 1
#             print(f"🔄 正在进行第 {attempt} 次重试...")
#             time.sleep(RETRY_DELAY)

#     print("🛑 达到最大重试次数，连接失败")
#     return False

# def is_ws_connected(ws_conn):
#     try:
#         return ws_conn and ws_conn.sock and ws_conn.sock.connected
#     except:
#         return False

# def start_heartbeat(ws, interval=20):
#     def run():
#         while True:
#             try:
#                 ws.ping()
#             except Exception as e:
#                 print("💥 ping 失败:", e)
#                 break
#             time.sleep(interval)
#     threading.Thread(target=run, daemon=True).start()




def audio_recording():
    global is_recording
    global ws
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
    try:
        while is_recording:
            data = stream.read(CHUNK)
            ws.send(data, opcode=websocket.ABNF.OPCODE_BINARY)  # 用 binary 发送音频流
    except Exception as e:
        print("录音异常:",e)
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()
        print("录音已停止，资源已释放")

def audio(request):
    global is_recording, recording_thread
    global ws
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
            ws.send("AUDIO_EOF")
        # else:
        #     ctx['rlt'] = '无效操作或状态不变。'

    return render(request, "audio.html", ctx)

def text_trans(text):
    global ws
    message = {"type":'text',"data":text}
    ws.send(json.dumps(message))
    print("简历发送成功")


def ai_interview_page(request):
    global ws
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
    ws.send(json.dumps({"type": 'control'}))
    return render(request, 'audio.html', {
        'rlt': '未开始',
        'status': '未连接',
        'pdf_message': pdf_message,
    })


def receive_tts():
    global ws
    tmp_message = 'START'
    p = pyaudio.PyAudio()
    try:
        ws.send(tmp_message)
        while True:
            stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True)

            while True:
                message = ws.recv()

                if isinstance(message,str) and message == "TTS_EOF":
                    print("播报完成")
                    break
                elif isinstance(message, bytes):
                    stream.write(message)
    
    except Exception as e:
        print('播报出错:', e)
    finally:
        if stream:
            stream.stop_stream()
            stream.close()
        p.terminate()
def start(request):
    if request.method == "POST":
        connect_websocket_audio()
        connect_websocket_video()
        recording_thread = threading.Thread(target=receive_tts)
        recording_thread.start()
        return render(request, 'audio.html')
    return render(request, 'start.html')



def video_streaming():
    global is_streaming
    global video_ws
    cap = cv2.VideoCapture(0)  # 默认摄像头
    
    try:
        # 连接 WebSocket 服务器
        # ws = websocket.create_connection("ws://localhost:8765")
        # ws = websocket.create_connection(WS_video_URL)
        # print("WebSocket 连接成功，开始发送视频数据...")
        
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
                video_ws.send(buffer.tobytes(), opcode=websocket.ABNF.OPCODE_BINARY)
                
                # 控制帧率 (30fps)
                time.sleep(1/30)
        
        finally:
            # 发送结束标志
            try:
                video_ws.send("EOF")
                print("已发送结束标志")
            except:
                print("发送结束标志失败")
            video_ws.close()
            print("WebSocket 连接已关闭")
    
    finally:
        cap.release()
        print("摄像头已释放")

def video(request):
    global is_streaming, streaming_thread
    global video_ws
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
