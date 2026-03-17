# from dotenv import load_dotenv
# from elevenlabs.client import ElevenLabs
# from elevenlabs.play import play
# import os

# load_dotenv()

# elevenlabs = ElevenLabs(
#   api_key=os.getenv("ELEVENLABS_API_KEY"),
# )

# audio = elevenlabs.text_to_speech.convert(
#     text="The first move is what sets everything in motion.",
#     voice_id="JBFqnCBsd6RMkjVDRZzb",
#     model_id="eleven_multilingual_v2",
#     output_format="mp3_44100_128",
# )

# OUTPUT_FILE = "test_output.mp3"

# with open(OUTPUT_FILE, "wb") as f:
#     for chunk in audio:
#         f.write(chunk)

# print(f"Saved to {OUTPUT_FILE}")



from gtts import gTTS

text = """今日は天気について話します。
今日はとてもいい天気です。空は青くて、少し暖かいです。
春になると、花が咲いて、とてもきれいですね。
でも、時々雨も降ります。雨の日は少し寒くて、傘が必要です。
夏はとても暑くなります。水をたくさん飲んでください。
天気は毎日変わるので、天気予報をチェックすることが大切です。
それでは、よい一日を過ごしてください。"""

tts = gTTS(text=text, lang='ja')
tts.save("japanese_weather.mp3")