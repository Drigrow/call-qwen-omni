# Call qwen-omni

A python file that calls qwen-omni api for multimedia in/output. Now only images and audios available. Videos may support in the future.

*No compatibility tests run. If you encounter any compatibility issues, solve it yourself :)

## Usage

- Download `qwen.py`
- Install necessary libs by:
```bash
pip install openai numpy soundfile pyaudio keyboard pyautogui
```
- Edit your api key in `qwen.py` ( replace `api_key="YOUR-ALIYUN-API-KEY"`)
- Run the code

## Commands available:
```txt
/mode - Change output mode (text, audio, both)
/history - Set the number of history messages to keep
/clear - Clear chat history
/show - Show current chat history
/screen - Take a screenshot and send it to the model with optional content
/help - Show this help message
/exit - Exit the program
```

## p.s.
There is limited Chinese prompt which may wrongly display under non-utf-8 systems. You may modify the prompts so they would best suit your work.

## p.p.s
This is a sample program that I'm testing if qwen-omni suits my need on a voice assistant. The answer is apparently yes. The running cost is low and little compute it requires to run the code, furthermore, the answer is amazing given the params. I would be working on it and implement it to a voice assistant someday. A smarter Siri!(?
