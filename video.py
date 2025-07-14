import cv2  
import time
import websocket
import threading

# 实现长时间录制

is_streaming = True
video_ws = None

def start_heartbeat(ws):
    def run():
        while True:
            try:
                ws.ping()
                print('发送一次心跳')
            except Exception as e:
                print("心跳失败:", e)
                break
            time.sleep(20)  # 每 20 秒发送 ping
    threading.Thread(target=run, daemon=True).start()


def video_streaming():
    global is_streaming
    global video_ws
    cap = cv2.VideoCapture(0)  # 默认摄像头
    
    try:
        if video_ws is None:
            video_ws = websocket.create_connection('ws://10.110.147.177:8765/ws/video')
            print('连接成功')
            start_heartbeat(video_ws)
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

if __name__ == '__main__':
    video_streaming()
    

