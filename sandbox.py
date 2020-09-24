from gtts import gTTS 
import os
from playsound import playsound

speech = gTTS(text="Hallo Welt", lang="de", slow=False)

speech.save("test.mp3")
playsound("test.mp3")