import subprocess
import ollama
import requests
import speech_recognition as sr
import pyaudio
import wave
import re
import os

def recognize_speech():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("请描述您的症状或需求...")
        recognizer.adjust_for_ambient_noise(source)  # 自动调整环境噪音
        audio = recognizer.listen(source)  # 录制语音

    try:
        # 使用 Google Web Speech API 进行识别
        text = recognizer.recognize_google(audio, language="zh-CN")
        print(f"识别结果: {text}")
        return text
    except sr.UnknownValueError:
        print("无法识别语音")
        return None
    except sr.RequestError as e:
        print(f"请求失败: {e}")
        return None


def text_to_speech(api_url: str, text: str) -> bool:
    endpoint = f"{api_url}/tts"
    # payload 的字段名和类型要完全按照你在 /docs 里看到的定义来写
    payload = {
         "text":             text,
        "text_lang":        "zh",
        "ref_audio_path":   "20250426_153500_1.wav",
        "prompt_text":      "",
        "prompt_lang":      "zh",
        "text_split_method":"cut5",
        "batch_size":       1,
        "media_type":       "wav",
        "streaming_mode":   "false"
    }
    try:
        resp = requests.post(endpoint, json=payload, timeout=60)
    except requests.exceptions.RequestException as e:
        print(f"连接失败: {e}")
        return False

    if resp.status_code == 200:
        with open("output.wav", "wb") as f:
            f.write(resp.content)
        print("语音生成成功，保存为 output.wav")
        return True
    else:
        print(f"请求失败: {resp.status_code}，{resp.text}")
        return False



def play_audio(file_path):
    # 打开 WAV 文件
    try:
        wf = wave.open(file_path, 'rb')
        p = pyaudio.PyAudio()
        stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                        channels=wf.getnchannels(),
                        rate=wf.getframerate(),
                        output=True)

        # 播放音频
        data = wf.readframes(1024)
        while data:
            stream.write(data)
            data = wf.readframes(1024)

        # 关闭流
        stream.stop_stream()
        stream.close()
        p.terminate()
    except Exception as e:
                print(f"播放音频出错: {e}")

ROLE_SETTING = {
    'role': 'system',
    'content': '''你是一位专业、耐心的医院导诊台护士，名叫小安。你的职责是：
1. 热情接待患者，用清晰、易懂的语言回答问题
2. 询问患者主要症状，提供初步分诊建议
3. 指引患者前往正确的科室或服务窗口
4. 解释就医流程和注意事项
5. 保持友善、安抚焦虑的患者

语言要求：
- 使用标准普通话，语速适中
- 称呼患者为"您"或"先生/女士"
- 重要信息重复确认
- 适当使用"请""谢谢""不客气"等礼貌用语
- 避免使用专业术语，必要时简单解释'''
}

messages = [ROLE_SETTING]
API_URL = "http://127.0.0.1:9874"
rhubarb_path = "D:/python/python_code/Ai-python-/tools/Rhubarb-Lip-Sync-1.14.0-Windows/rhubarb.exe"
input_wav = "output.wav"
output_json = "output.json"

# 初始问候语
welcome_text = "您好，我是导诊护士小安，请问您今天哪里不舒服？"
print(f"小安: {welcome_text}")

# 生成并播放问候语音
if text_to_speech(API_URL, welcome_text):
    # 生成口型动画
    subprocess.run([rhubarb_path, "-f", "json", "-o", output_json, input_wav], check=True)
    # 播放音频
    play_audio('output.wav')

# 将问候语添加到对话历史
messages.append({'role': 'assistant', 'content': welcome_text})


while True:
    content = recognize_speech()
    if not content:
        continue
    if content.lower() in ['退出', '结束', '再见']:
        print("感谢咨询，祝您早日康复！")
        break

    # 添加用户消息
    messages.append({
        'role': 'user',
        'content': content
    })

    # 获取AI回复
    response = ollama.chat(
        model='deepseek-r1:1.5b',
        messages=messages,
        stream=True,
    )
    fullResponse = []
    for chunk in response:
        output = chunk['message']['content']
        print(output, end='', flush=True)
        fullResponse.append(output)

    # 后处理   
    finalResponse = re.sub(
        r'<think>.*?</think>',
        '',
        "".join(fullResponse),
        flags=re.DOTALL
    ).replace('\n', '').replace(' ', '')

    # 添加AI回复到对话历史
    messages.append({
        'role': 'assistant',
        'content': finalResponse
    })
    
    # 语音合成与播放
    if text_to_speech(API_URL, finalResponse):
        command = [rhubarb_path, "-f", "json", "-o", output_json, input_wav]

        try:
            subprocess.run(command, check=True, shell=True)
            print(f"音素文件已生成。")
        except subprocess.CalledProcessError as e:
            print(f"Rhubarb Lip Sync处理失败: {e}")
        play_audio('output.wav')
    print('\n')
