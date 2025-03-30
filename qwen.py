import os
from openai import OpenAI
import base64
import numpy as np
import soundfile as sf
import time
import pyaudio
import wave
import keyboard
import pyautogui
import tempfile
from datetime import datetime

client = OpenAI(
    api_key="YOUR-ALIYUN-API-KEY",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

chat_history = []
modes = ["text", "audio", "both"]
mode = "text"
history_limit = 8 

def record_audio():
    """
    Record audio from microphone until Enter key is pressed.
    Returns the path to the recorded audio file.
    """
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    CHUNK = 1024
    WAVE_OUTPUT_FILENAME = "input_audio.wav"
    
    print("Recording... Press Enter to stop.")
    
    audio = pyaudio.PyAudio()
    
    stream = audio.open(format=FORMAT, channels=CHANNELS,
                        rate=RATE, input=True,
                        frames_per_buffer=CHUNK)
    
    frames = []
    recording = True
    
    def on_press(key):
        if key.name == 'enter':
            return False
        return True

    keyboard.hook(on_press)
    
    try:
        while recording:
            try:
                data = stream.read(CHUNK)
                frames.append(data)
                if not keyboard.is_pressed('enter'):
                    continue
                else:
                    recording = False
            except KeyboardInterrupt:
                recording = False
    finally:
        keyboard.unhook_all()
    
    print("Recording stopped.")
    
    stream.stop_stream()
    stream.close()
    audio.terminate()
    
    wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(audio.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    
    return WAVE_OUTPUT_FILENAME

def take_screenshot():
    """
    Capture a screenshot and save it to a temporary file.
    Returns the path to the screenshot file.
    """

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_dir = tempfile.gettempdir()
    screenshot_path = os.path.join(temp_dir, f"screenshot_{timestamp}.png")
    

    screenshot = pyautogui.screenshot()
    screenshot.save(screenshot_path)
    
    print(f"Screenshot saved to {screenshot_path}")
    return screenshot_path

def encode_audio(audio_path):
    """
    Encode audio file to base64 string in the format required by the API.
    """
    with open(audio_path, "rb") as audio_file:
        return f"data:;base64,{base64.b64encode(audio_file.read()).decode('utf-8')}"

def encode_image(image_path):
    """
    Encode image file to base64 string.
    """
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def get_response(content="你好！你叫什么名字？", audio_in=False, audio_path=None, audio_out=False, history_msgs=None):
    modalities_preset = ["text"]
    if audio_out == True:
        modalities_preset = ["text", "audio"]
    
    messages = []
    
    messages.append({
        "role": "system",
        "content": [{"type": "text", "text": "You are a helpful assistant."}]
    })
    
    if history_msgs and len(history_msgs) > 0:
        messages.extend(history_msgs)
    
    if audio_in and audio_path:
        base64_audio = encode_audio(audio_path)
        
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "input_audio",
                    "input_audio": {
                        "data": base64_audio,
                        "format": "wav",
                    },
                },
                {"type": "text", "text": "用户与你正在进行语音对话，这是用户的音频"},
            ],
        })
    else:
        messages.append({"role": "user", "content": f"{content}"})
    
    completion = client.chat.completions.create(
        model="qwen-omni-turbo",
        messages=messages,
        modalities=modalities_preset,
        audio={"voice": "Cherry", "format": "wav"},
        stream=True,
        stream_options={"include_usage": True}
    )
    return completion

def process_screenshot_command(text_input):
    """
    Process the /screen command, take a screenshot, and send it to the model.
    """
    global chat_history, mode, history_limit
    
    content = text_input[7:].strip() if len(text_input) > 7 else ""
    
    if not content:
        content = input("What would you like to ask about the screenshot? (press Enter for default): ")
        if not content:
            content = "图中是什么？用户可能想问什么？"
    
    try:
        screenshot_path = take_screenshot()
        print("Processing your screenshot...")
        
        base64_image = encode_image(screenshot_path)
        

        chat_history.append({"role": "user", "content": f"[Screenshot] {content}"})
        
        history_msgs = []
        if history_limit > 0 and len(chat_history) > 1:
            start_idx = max(0, len(chat_history) - (history_limit * 2))
            history_msgs = chat_history[start_idx:-1]
        
        messages = []
        
        messages.append({
            "role": "system",
            "content": [{"type": "text", "text": "You are a helpful assistant."}]
        })
        
        if history_msgs and len(history_msgs) > 0:
            messages.extend(history_msgs)
        
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{base64_image}"},
                },
                {"type": "text", "text": content},
            ],
        })
        
        audio_out = mode != "text"
        
        completion = client.chat.completions.create(
            model="qwen-omni-turbo",
            messages=messages,
            modalities=["text", "audio"] if audio_out else ["text"],
            audio={"voice": "Cherry", "format": "wav"} if audio_out else None,
            stream=True,
            stream_options={"include_usage": True}
        )
        
        if audio_out and mode == "both":
            response_text = audio_output(completion, text="stream")
        elif audio_out and mode == "audio":
            response_text = audio_output(completion, text=None)
        else:
            response_text = text_output(completion)
        
        chat_history.append({"role": "assistant", "content": response_text})
        
        if history_limit > 0 and len(chat_history) > history_limit * 2:
            chat_history = chat_history[-(history_limit * 2):]
        
        try:
            os.remove(screenshot_path)
        except:
            pass
            
    except Exception as e:
        print(f"Error processing screenshot: {e}")
    
    return True

def audio_output(completion, text=None):
    transcript_text = ""
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16,
                    channels=1,
                    rate=24000,
                    output=True)
    for chunk in completion:
        if chunk.choices:
            if hasattr(chunk.choices[0].delta, "audio"):
                try:
                    audio_string = chunk.choices[0].delta.audio["data"]
                    wav_bytes = base64.b64decode(audio_string)
                    audio_np = np.frombuffer(wav_bytes, dtype=np.int16)
                    stream.write(audio_np.tobytes())
                except Exception as e:
                    if text == "stream":
                        print(chunk.choices[0].delta.audio["transcript"], end="")
                    transcript_text += chunk.choices[0].delta.audio["transcript"]
    if text == "text":
        print(transcript_text)
    print(time.time())

    time.sleep(0.8)
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    return transcript_text

def text_output(completion):
    full_response = ""
    for chunk in completion:
        if chunk.choices:
            try:
                transcript = chunk.choices[0].delta.audio["transcript"]
                print(transcript, end="")
                full_response += transcript
            except:
                if hasattr(chunk.choices[0].delta, "content") and chunk.choices[0].delta.content is not None:
                    print(chunk.choices[0].delta.content, end="")
                    full_response += chunk.choices[0].delta.content
        else:
            print("\n", chunk.usage)
    
    return full_response

print("Input text to talk to qwen-omni, or press Enter (with no text) to record audio. Text result default, change mode by:\n/mode\nYou may find help by:\n/help.")

mode_usage = '''Usage:
    /mode [mode]
Commands:
    text          only text output
    audio         only audio output
    both          both text&audio output
'''

history_usage = '''Usage:
    /history [number]
Commands:
    number        set the number of history messages to keep (0 to disable history)
'''

helps = '''Available commands:
/mode - Change output mode (text, audio, both)
/history - Set the number of history messages to keep
/clear - Clear chat history
/show - Show current chat history
/screen - Take a screenshot and send it to the model with optional content
/help - Show this help message
/exit - Exit the program
'''


while True:
    text_input = input("You:\n")
    
    if text_input.startswith("/"):
        if text_input.startswith("/mode"):
            split = text_input.split(" ")
            try:
                if len(split) < 2:
                    print(mode_usage)
                    continue
                else:
                    command = split[1]
                    if command not in modes:
                        print("Unrecognized command for /mode, try again\n")
                    else:
                        mode = command
                        print(f"Mode set to {mode}.\n")
                        continue
            except IndexError:
                print(mode_usage)
                continue
        
        elif text_input.startswith("/hist"):
            split = text_input.split(" ")
            try:
                if len(split) < 2:
                    print(history_usage)
                    print(f"Current history limit: {history_limit} messages")
                else:
                    command = int(split[1])
                    if command >= 0:
                        history_limit = command
                        if len(chat_history) > history_limit * 2 and history_limit > 0:
                            chat_history = chat_history[-(history_limit * 2):]
                        print(f"History set to {history_limit} messages")
                    else:
                        print("History limit must be a non-negative number\n")
            except ValueError:
                print("History limit must be a number\n")
            continue
        
        elif text_input.startswith("/clear"):
            chat_history = []
            print("Chat history cleared.")
            continue
        
        elif text_input.startswith("/show"):
            if not chat_history:
                print("No chat history available.")
            else:
                print("\n----- CHAT HISTORY -----")
                for i, msg in enumerate(chat_history):
                    role = msg["role"].capitalize()
                    content = msg["content"]
                    print(f"{i+1}. {role}: {content}")
                print("-----------------------\n")
            continue
        
        elif text_input.startswith("/help"):
            print(helps)
            continue
        
        elif text_input.startswith("/exit"):
            print("Goodbye!")
            exit()
        
        elif text_input.startswith("/screen"):
            process_screenshot_command(text_input)
            continue
        
        else:
            print(f"Unrecognized command: {text_input}, try:\n/help")
            continue
    
    elif text_input == '':
        print("Starting audio input...")
        try:
            audio_path = record_audio()
            print("Processing your voice message...")
            
            chat_history.append({"role": "user", "content": "[Voice Message]"})
            
            history_msgs = []
            if history_limit > 0 and len(chat_history) > 1:
                start_idx = max(0, len(chat_history) - (history_limit * 2))
                history_msgs = chat_history[start_idx:-1]
            
            audio_out = mode != "text"
            completion = get_response(audio_in=True, audio_path=audio_path, audio_out=audio_out, history_msgs=history_msgs)
            
            if audio_out and mode == "both":
                response_text = audio_output(completion, text="stream")
            elif audio_out and mode == "audio":
                response_text = audio_output(completion, text=None)
            else:
                response_text = text_output(completion)
            
            chat_history.append({"role": "assistant", "content": response_text})
            
            if history_limit > 0 and len(chat_history) > history_limit * 2:
                chat_history = chat_history[-(history_limit * 2):]
                
        except Exception as e:
            print(f"Error recording or processing audio: {e}")
        
        continue
    
    else:
        audio_out = mode != "text"
        

        history_msgs = []
        if history_limit > 0 and chat_history:
            start_idx = max(0, len(chat_history) - (history_limit * 2))
            history_msgs = chat_history[start_idx:]
        
        chat_history.append({"role": "user", "content": text_input})
        

        completion = get_response(content=text_input, audio_out=audio_out, history_msgs=history_msgs)
        
        if audio_out and mode == "both":
            response_text = audio_output(completion, text="stream")
        elif audio_out and mode == "audio":
            response_text = audio_output(completion, text=None)
        else:
            response_text = text_output(completion)
        
        chat_history.append({"role": "assistant", "content": response_text})
        
        if history_limit > 0 and len(chat_history) > history_limit * 2:
            chat_history = chat_history[-(history_limit * 2):]
