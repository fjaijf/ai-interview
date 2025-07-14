# from socket import *
# # 1.创建套接字
# tcp_socket = socket(AF_INET,SOCK_STREAM)
# # 2.准备连接服务器，建立连接
# serve_ip = "10.110.147.177"
# serve_port = 8000  #端口，比如8000
# tcp_socket.connect((serve_ip,serve_port))  # 连接服务器，建立连接,参数是元组形式
# #准备需要传送的数据
# send_data = "今天是2021年08月29日，给服务器端发送数据了"
# tcp_socket.send(send_data.encode("gbk")) 
# #从服务器接收数据
# #注意这个1024byte，大小根据需求自己设置
# from_server_msg = tcp_socket.recv(1024)
# #加上.decode("gbk")可以解决乱码
# print(from_server_msg.decode("gbk"))  
# #关闭连接
# tcp_socket.close()


import socket
import pyaudio

HOST = '10.110.147.177'  # 服务器IP
PORT = 8000

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

def main():
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        print("连接服务器成功，开始发送音频数据...")
        
        try:
            while True:
                data = stream.read(CHUNK)
                s.sendall(data)
        except KeyboardInterrupt:
            print("停止录音")
        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()

if __name__ == '__main__':
    main()
