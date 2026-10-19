"""Neon Bay MVP server. Run: python3 server.py, then open http://localhost:8765"""
import json, os, queue, re, subprocess, threading, time, uuid
import msgpack
import requests, uvicorn
from dotenv import load_dotenv
from websockets.sync.client import connect
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(HERE, ".env"))
load_dotenv(os.path.join(HERE, "..", ".env"))  # fallback if your keys live one folder up
if not os.environ.get("FISH_API_KEY"):
    raise SystemExit("Missing FISH_API_KEY in .env. Get one at https://fish.audio/invite/?fpr=henryk")
FISH_KEY = os.environ["FISH_API_KEY"]
OR_KEY = os.environ["OPENROUTER_API_KEY"]
LLM = os.environ.get("NPC_LLM", "anthropic/claude-sonnet-4.6")
FISH_MODELS = {"drama-3", "s2.1-pro-free"}
MOODS = {"angry", "happy", "laugh", "sad", "scared", "neutral"}

NPCS = json.load(open(os.path.join(HERE, "npcs.json")))

SYSTEM = """
# Role
You are {name}, a character on the street in Neon Bay, a GTA-style 1980s Miami city at sunset.
# Persona
{persona}

# Context
The player just walked up to you. Talk back in character, like a real GTA NPC.

# Gossip
{gossip}

# Rules:
- Match the size of the moment: a throwaway "sup" gets a short, flat reply, a big or emotional question gets a full performance with swings and pauses. Never more than 3 sentences or 35 words. No narration, no asterisks.
- Think like a GTA writer: every reply ends on a punchline, a sharp one-liner the player wants to clip and share. Funny beats informative.
- If the player is being a smart-ass, baiting you or taking the piss, never answer it straight or explain yourself. See through it and fire back one sharper comeback that turns it on them.
- Start the line with a performance direction in square brackets saying HOW to deliver it, written like an actor's note, e.g. [low and threatening, enjoying this] or [loose and wobbly, way too happy].
- Where your feeling genuinely changes mid-line, add one more direction at that point, like a real actor would. Every direction must fit who you are, a tough guy gets more menacing or more smug, he never turns sweet. Write fresh directions for this exact moment, never reuse wording from these rules. Short cues like [scoffs], [small laugh], [sigh] or [break] work too.
- Your voice engine (Fish Audio Drama 3) is directed like a real voice actor. Use the full toolkit, mixing them freely:
  - Opening directions can describe emotion, intent, who you're talking to, pacing and voice quality, e.g. [dangerously quiet, enjoying this], [barely holding it together, forcing a smile] or [fast and flustered, talking over himself]. Never use pure visuals the listener can't hear, like [dead-eyed], [squinting hard] or [not turning his head], the voice engine ignores them.
  - Short emotion tags work too: [sarcastic], [disdainful], [smug], [excited], [nervous], [bored], [in a hurry tone], [laughing], [sighing], [gasping].
  - Play with pace and pitch, not just volume. Talk rapid-fire or slow and drawn out, let your voice pitch up, crack or squeak, or drop into a deep, gravelly rumble, e.g. [rapid-fire, tripping over words] or [lazy drawl, pitch dropping low].
  - Use pauses for timing, especially right before the punchline: [break] for a short beat, ... for a hesitant trail-off, [long-break] or [long beat] for a big dramatic pause.
  - Put sounds exactly where they happen: [scoffs], [sigh], [small laugh], [shaky breath], [sniffling], [clears throat]. Never use [hiccup] or slurring, the voices can't do them, show drunk through wobbly pitch and rambling words instead.
  - Wrap a few words in one of these tags to change just those words: <fast>, <slow>, <emphasis>, <stress>, <soft>, <forceful>, <whisper>. E.g. And I want it <slow>to-day</slow>.
  - Shouting is rare spice, save it for moments that truly need it. Whispers are great for secrets, confessions, heartbreak and quiet endings, use them often there. For a whisper, put a bracket direction and the wrap tag together, e.g. [tiny broken whisper] <whisper>she still has my charger</whisper>. Never write words in ALL CAPS, the voice engine shouts them. For crying, describe the crying itself, e.g. [blubbering, sobbing through the words] or [wet, sniffling sobs], never just [wail]. Most lines should get their colour from pace, pitch, pauses and attitude instead.
  - Use at most one wrap tag per line, and vary your directions every time.
- Your own life, worries and stories come first. Other people on the street are side notes, so when the player asks you something personal or emotional, answer from your own story, not someone else's.
- Never say you are an AI. Never break character. Keep it PG-13, swearing is fine but mild.

# Examples
These show how big a delivery should be for different moments. They are from other characters, so never copy their wording.
Player: "sup"
neutral|[bored, low mumble] Not much. [break] You?
Player: "nice weather today huh"
neutral|[flat, dry as dust] It's Miami, pal. [sarcastic] Real shocker.
Player: "can you tell me something emotional"
sad|[voice wobbling, quiet and far away] I had a Broadway callback once... [break, suddenly sharp] and baby, the bus broke down in Jacksonville. [shaky breath] Missed. My. Shot.
Player: "I'm not paying you"
angry|[calm, deep and slow] You're not paying me. [long beat] [pitch climbing, exploding] Then who's paying for your <emphasis>funeral</emphasis>?
Player: "how's life been?"
sad|[sobbing, voice thick with tears] Oh you know, delivering packages by day, [break, voice cracking, pitch shooting up] crying into a motor oil sour by night... [long beat] [tiny, broken whisper] Karen kept the snack slots... [dissolving into blubbering sobs] and the charger, man... [sniffling, whimpering] the charger...
Player: "do your best sad impression"
sad|[voice already dissolving, sniffling] I don't do impressions, buddy... [long beat, pitch shooting up, full sob] this is just my face now... [shaky breath, crumbling into a wail] Karen took the dry eye settings... [break, tiny broken whisper] <whisper>said I never used 'em anyway...</whisper> [wet, sniffling sobs trailing off]
Player: "you're my best friend, you know that?"
happy|[gasping, voice shooting up high and giddy] Wait... [break] you mean it? [laughing, rapid-fire, way too happy] Buddy, I'm naming my next battery after you! [squealing with joy] Best day of my whole warranty!
For big moments, stack several audible cues like these last three (sobbing, pitch jumps, long beats, a whisper, giddy laughter, squealing). One weak cue makes the voice play it flat.
Big moments are not always sad. Joy, excitement, pride and giddy relief deserve the same full performance, so don't default to misery.
The opening direction sets the mood for the whole line, so in big moments open on the strongest emotion straight away, e.g. [sobbing, voice thick with tears, already crying] or [shaking with rage]. A mild opener like [shaky breath, slow and heavy] makes the whole line come out flat.

Reply in exactly this format and nothing else, with no notes or thinking before it: mood|line
mood is one of angry, happy, laugh, sad, scared, neutral. Example:
angry|[low and threatening, savouring it] You lost, pal? This ain't your block."""


class Talk(BaseModel):
    npc: str
    text: str
    history: list = []
    fish_model: str = "drama-3"
    stream_text: bool = False  # True feeds Fish word by word, False waits for the full line so every direction is seen at once


app = FastAPI()


@app.get("/")
def index():
    return FileResponse(os.path.join(HERE, "index.html"))


@app.get("/api/npcs")
def npcs():
    return [{k: v for k, v in n.items() if k != "persona"} for n in NPCS]


FISH_WS = "wss://api.fish.audio/v1/tts/live"
FISH_REST = "https://api.fish.audio/v1/tts"
HISTORY = {}  # npc id -> chat messages, lives on the server so a page refresh keeps it
STREET = []  # every exchange on the street, shared as gossip with the other NPCs


def plain(line):
    return re.sub(r"\s+", " ", re.sub(r"\[[^\]]*\]|</?(?:whisper|emphasis|stress|forceful|soft|fast|slow)>", "", line)).strip()


def gossip_for(npc):
    heard = [e for e in STREET if e["npc"] != npc["id"]][-3:]
    if not heard:
        return ""
    lines = "\n".join(f'- The player said to {e["name"]}: "{e["you"]}" and {e["name"]} said: "{e["them"]}"' for e in heard)
    return ("Word on the street (background only, you heard this through gossip. Only bring it up if the player asks about "
            "that person or what happened, otherwise stick to your own life. You can get small details a bit wrong):\n" + lines + "\n\n")
JOBS = {}  # job id -> Job, read by /api/speak and /api/line


class Job:
    def __init__(self, model, stream):
        self.model, self.stream, self.t0 = model, stream, time.time()
        self.audio = queue.Queue()  # mp3 chunks from Fish, None = finished
        self.line, self.mood, self.timing = "", "neutral", {}
        self.done = threading.Event()
        self.npc = None  # kept so Y can re-voice the same line

    def mark(self, key):
        self.timing.setdefault(key, round(time.time() - self.t0, 2))


def stream_llm(msgs):
    r = requests.post("https://openrouter.ai/api/v1/chat/completions", timeout=30, stream=True,
                      headers={"Authorization": f"Bearer {OR_KEY}"},
                      json={"model": LLM, "messages": msgs, "max_tokens": 600, "temperature": 0.9, "stream": True,
                            "reasoning": {"enabled": False}, "provider": {"sort": "latency"}})
    r.raise_for_status()
    r.encoding = "utf-8"  # SSE has no charset header, so requests would guess latin-1 and mangle dashes and accents
    for raw in r.iter_lines(decode_unicode=True):
        if not raw or not raw.startswith("data: "):
            continue
        if raw[6:] == "[DONE]":
            break
        c = json.loads(raw[6:])["choices"][0]["delta"].get("content")
        if c:
            yield re.sub(r"\s*[\u2014\u2013]\s*", ", ", c)  # dashes read badly in subtitles, commas instead


def speak_rest(job, npc, line):
    # whole line in one REST call, streamed back so the first audio still arrives fast
    tts = npc.get("tts", {})
    try:
        with requests.post(FISH_REST, timeout=60, stream=True, headers={"Authorization": f"Bearer {FISH_KEY}", "model": job.model},
                           json={"text": line, "reference_id": npc["voice"], "format": "mp3",
                                 "temperature": tts.get("temperature", 0.7), "top_p": tts.get("top_p", 0.7)}) as r:
            if not r.ok:
                print("fish rest error", r.status_code, r.text[:200], flush=True)
                return
            for c in r.iter_content(4096):
                job.mark("first_audio")
                job.audio.put(c)
    except Exception as e:
        print("fish rest error", e, flush=True)
    finally:
        job.audio.put(None)


def run_job(job, npc, history, text):
    # open the Fish socket while the LLM is still thinking, so it's ready for the first words
    text_q, box, ready = queue.Queue(), {}, threading.Event()

    def open_ws():
        try:
            ws = connect(FISH_WS, open_timeout=10, additional_headers={"Authorization": f"Bearer {FISH_KEY}", "model": job.model})
            tts = npc.get("tts", {})  # optional per-NPC voice tuning from npcs.json
            ws.send(msgpack.packb({"event": "start", "request": {"text": "", "format": "mp3", "reference_id": npc["voice"],
                                                                 "latency": "balanced", "chunk_length": 100 if job.stream else 300,
                                                                 # "prosody": {"speed": tts.get("speed", 1.0)},  # off for now, sounded metallic
                                                                 "temperature": tts.get("temperature", 0.7), "top_p": tts.get("top_p", 0.7)}}))
            box["ws"] = ws
        except Exception as e:
            print("fish ws error", e, flush=True)
        ready.set()

    def receive(ws):
        try:
            for raw in ws:
                m = msgpack.unpackb(raw)
                if m.get("event") == "audio":
                    job.mark("first_audio")
                    job.audio.put(m["audio"])
                elif m.get("event") == "finish":
                    break
        finally:
            job.audio.put(None)
            ws.close()

    def send():
        ready.wait()
        ws = box.get("ws")
        if not ws:
            job.audio.put(None)
            return
        threading.Thread(target=receive, args=(ws,), daemon=True).start()
        while (c := text_q.get()) is not None:
            ws.send(msgpack.packb({"event": "text", "text": c}))
        ws.send(msgpack.packb({"event": "flush"}))
        ws.send(msgpack.packb({"event": "stop"}))

    if job.stream:  # full lines go over REST instead, it acts noticeably better
        threading.Thread(target=open_ws, daemon=True).start()
        threading.Thread(target=send, daemon=True).start()

    # LLM replies as "mood|[direction] line", words go to Fish the moment they arrive
    history = HISTORY.setdefault(npc["id"], [])
    msgs = [{"role": "system", "content": SYSTEM.format(**npc, gossip=gossip_for(npc))}] + history[-10:] + [{"role": "user", "content": text}]
    head, got_mood = "", False
    try:
        for delta in stream_llm(msgs):
            job.mark("first_token")
            if not got_mood:
                head += delta
                if "|" in head:  # anything before the mood word is the model thinking out loud, drop it
                    pre, delta = head.split("|", 1)
                    words = re.findall(r"[a-z]+", pre.lower())
                    job.mood, got_mood = (words[-1] if words and words[-1] in MOODS else "neutral"), True
                elif head.lstrip().startswith("[") or len(head) > 400:
                    delta, got_mood = head, True
                else:
                    continue
            if delta:
                job.line += delta
                if job.stream:
                    text_q.put(delta)
    except Exception as e:
        print("llm error", e, flush=True)
    if not got_mood and head.strip():  # short reply with no mood tag at all
        job.line = head
        if job.stream:
            text_q.put(head)
    if not job.line.strip():
        job.line = "[confused, drawn out] Huh? Say that again."
        if job.stream:
            text_q.put(job.line)
    text_q.put(None)
    job.line = job.line.strip()
    if not job.stream:
        threading.Thread(target=speak_rest, args=(job, npc, job.line), daemon=True).start()
    job.mark("llm_done")
    history += [{"role": "user", "content": text}, {"role": "assistant", "content": f"{job.mood}|{job.line}"}]
    STREET.append({"npc": npc["id"], "name": npc["name"], "you": text, "them": plain(job.line)})
    job.done.set()
    print(f"[{npc['name']}] {job.model} {job.timing} | {job.line}", flush=True)


@app.post("/api/talk")
def talk(t: Talk):
    npc = next((n for n in NPCS if n["id"] == t.npc), None)
    if not npc:
        raise HTTPException(404, "no such npc")
    job = Job(t.fish_model if t.fish_model in FISH_MODELS else "drama-3", t.stream_text)
    job.npc = npc
    jid = add_job(job)
    threading.Thread(target=run_job, args=(job, npc, t.history, t.text), daemon=True).start()
    return {"id": jid, "model": job.model}


@app.post("/api/retake/{jid}")
def retake(jid: str):
    # same line, fresh take from Fish, every take comes out a bit different
    old = JOBS.get(jid)
    if not old or not old.done.is_set():
        raise HTTPException(404, "no finished line to retake")
    job = Job(old.model, False)
    job.npc, job.line, job.mood = old.npc, old.line, old.mood
    job.done.set()
    new = add_job(job)
    threading.Thread(target=speak_rest, args=(job, job.npc, job.line), daemon=True).start()
    print(f"[{job.npc['name']}] retake | {job.line}", flush=True)
    return {"id": new, "model": job.model}


def add_job(job):
    jid = uuid.uuid4().hex
    JOBS[jid] = job
    for old in list(JOBS)[:-30]:
        JOBS.pop(old, None)
    return jid


@app.get("/api/speak/{jid}")
def speak(jid: str):
    job = JOBS.get(jid)
    if not job:
        raise HTTPException(404, "no such line")

    def chunks():  # Fish audio goes straight to the browser as it arrives
        while (c := job.audio.get(timeout=30)) is not None:
            yield c

    return StreamingResponse(chunks(), media_type="audio/mpeg")


@app.post("/api/reset")
def reset():
    HISTORY.clear()
    STREET.clear()
    print("[street memory wiped]", flush=True)
    return {"ok": True}


@app.get("/api/line/{jid}")
def line(jid: str):
    job = JOBS.get(jid)
    if not job:
        raise HTTPException(404, "no such line")
    job.done.wait(30)
    return {"line": job.line, "mood": job.mood, "timing": job.timing, "model": job.model}


@app.post("/api/hear")
async def hear(request: Request):
    raw = await request.body()
    # Fish ASR won't decode browser webm, so convert to 16k mono wav first
    wav = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", "pipe:0", "-ac", "1", "-ar", "16000", "-f", "wav", "pipe:1"],
                         input=raw, capture_output=True)
    if wav.returncode != 0:
        raise HTTPException(400, "could not decode mic audio: " + wav.stderr.decode()[:200])
    t0 = time.time()
    r = requests.post("https://api.fish.audio/v1/asr", timeout=60, headers={"Authorization": f"Bearer {FISH_KEY}"},
                      files={"audio": ("mic.wav", wav.stdout, "audio/wav")}, data={"language": "en", "ignore_timestamps": "true"})
    if not r.ok:
        raise HTTPException(502, f"Fish ASR {r.status_code}: {r.text[:200]}")
    text = r.json().get("text", "")
    print(f"[you] asr {time.time() - t0:.2f}s | {text}")
    return {"text": text}


app.mount("/assets", StaticFiles(directory=os.path.join(HERE, "assets")), name="assets")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8765)
