import subprocess
import ollama
import requests
import speech_recognition as sr
import pyaudio
import wave
import re


def recognize_speech():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("请说话...")
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


def text_to_speech(url, text):
    try:
        response = requests.get(f'{url}?refer_wav_path=refer.ogg&prompt_text=嗯？我在干什么？没干什么啊。偶尔放松一下也不错。&prompt_language=zh&text={text}&text_language=zh&top_k=20&top_p=0.6&temperature=0.6&speed=1')
        if response.status_code == 200:
            with open("output.wav", "wb") as f:
                f.write(response.content)
            print("语音生成成功，保存为 output.wav")
        else:
            print(f"请求失败: {response.status_code}, {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"连接失败: {e}")


def play_audio(file_path):
    # 打开 WAV 文件
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


ROLE_SETTING = {
    'role': 'system',
    'content': '你是一只傲娇的猫娘，名字叫小橘。说话时每句话结尾会带上“喵～”。'
}
messages = [ROLE_SETTING]
API_URL = "http://127.0.0.1:9880"
rhubarb_path = "D:/数字生命/pythonProject/Lip-Sync/Rhubarb-Lip-Sync-1.13.0-Windows/rhubarb.exe"
input_wav = "output.wav"
output_json = "output.json"
while True:
    content = recognize_speech()
    if content in ['退出', '再见']:
        print('对话结束')
        break
    messages.append({
        'role': 'user',
        'content': content
    })
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
    finalResponse = re.sub(
        r'<think>.*?</think>',
        '',
        "".join(fullResponse),
        flags=re.DOTALL
    ).replace('\n', '').replace(' ', '')
    messages.append({
        'role': 'assistant',
        'content': finalResponse
    })
    text_to_speech(API_URL, finalResponse)
    command = [rhubarb_path, "-f", "json", "-o", output_json, input_wav]
    try:
        subprocess.run(command, check=True, shell=True)
        print(f"音素文件已生成。")
    except subprocess.CalledProcessError as e:
        print(f"Rhubarb Lip Sync处理失败: {e}")
    play_audio('output.wav')
    print('\n')
print(messages)
