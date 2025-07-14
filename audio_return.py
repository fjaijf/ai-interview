# import asyncio
# import websockets
# import pyaudio

# # 音频播放参数，跟你的音频格式匹配
# CHANNELS = 1
# RATE = 16000
# FORMAT = pyaudio.paInt16  # 2字节宽度对应SAMPLE_WIDTH=2

# async def receive_and_play_audio(uri):
#     p = pyaudio.PyAudio()
#     stream = p.open(format=FORMAT,
#                     channels=CHANNELS,
#                     rate=RATE,
#                     output=True)

#     async with websockets.connect(uri) as websocket:
#         print("连接成功，开始接收音频...")
#         try:
#             async for message in websocket:
#                 if isinstance(message, str) and message == "EOF":
#                     print("音频流结束")
#                     break
#                 # message是bytes，直接写入音频流播放
#                 stream.write(message)
#         except Exception as e:
#             print("异常:", e)

#     stream.stop_stream()
#     stream.close()
#     p.terminate()
#     print("播放结束")

# if __name__ == "__main__":
#     uri = "ws://10.110.147.177:8050"  # 替换成你的音频WebSocket地址
#     asyncio.run(receive_and_play_audio(uri))


import asyncio
import websockets
import pyaudio

CHANNELS = 1
RATE = 16000
FORMAT = pyaudio.paInt16

async def receive_and_play_audio(uri):
    p = pyaudio.PyAudio()
    while True:
        try:
            async with websockets.connect(uri,open_timeout=120) as websocket:
                print("✅ 已连接服务器，等待音频...")

                while True:
                    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True)

                    while True:
                        message = await websocket.recv()

                        if isinstance(message, str) and message == "EOF":
                            print("🎧 播放完成，继续等待下一段音频...\n")
                            break
                        elif isinstance(message, bytes):
                            stream.write(message)

                    stream.stop_stream()
                    stream.close()

                
        except (websockets.exceptions.InvalidStatusCode, asyncio.TimeoutError, OSError) as e:
            await asyncio.sleep(5)
        
        except Exception as e:
                    print("❌ 异常:", e)

    p.terminate()

if __name__ == "__main__":
    uri = "ws://10.110.147.177:8050"
    asyncio.run(receive_and_play_audio(uri))
