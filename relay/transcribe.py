# Usage: venv/bin/python transcribe.py <audio/video file>  -> prints transcript (language auto-detect, ru typical)
# Decodes with system ffmpeg (16k mono) to avoid PyAV API mismatches. Called by relay.py with a timeout.
import sys, subprocess, numpy as np
from faster_whisper import WhisperModel
raw=subprocess.run(["ffmpeg","-loglevel","error","-i",sys.argv[1],"-f","s16le","-ac","1","-ar","16000","-"],capture_output=True,check=True).stdout
audio=np.frombuffer(raw,np.int16).astype(np.float32)/32768.0
m=WhisperModel("small",device="cpu",compute_type="int8",cpu_threads=4)
segs,info=m.transcribe(audio,language=None,vad_filter=True,beam_size=1)
print(" ".join(s.text.strip() for s in segs).strip())
