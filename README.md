# Neon Bay: GTA-style NPCs that talk back

A tiny GTA-style street in your browser where every NPC actually talks back. Walk up, say anything into your mic, and they reply in character with a fully acted voice from [Fish Audio](https://fish.audio/invite/?fpr=henryk) Drama 3. They remember what you said, and they gossip about you to each other.

## What you need

- Python 3.10+
- [ffmpeg](https://ffmpeg.org) (`brew install ffmpeg` on Mac), used to convert your mic audio
- Chrome
- A [Fish Audio](https://fish.audio/invite/?fpr=henryk) API key, for the voices and speech-to-text
- An [OpenRouter](https://openrouter.ai) API key, for the model that writes the lines



## Setup

```
pip install -r requirements.txt
cp .env.example .env
```

Put your two keys in `.env`. No Fish account yet? [Sign up here](https://fish.audio/invite/?fpr=henryk) and grab a key from the API section. Then run:

```
python3 server.py
```

Open [http://localhost:8765](http://localhost:8765) in Chrome and allow the mic.

## Controls


| Key     | What it does                                                         |
| ------- | -------------------------------------------------------------------- |
| W A S D | Move (Shift sprint, C walk), drag the mouse to look                  |
| Hold T  | Talk to the nearest NPC                                              |
| H       | Hands-free: walk within 3m and just talk, it sends when you go quiet |
| Enter   | Type instead of talking                                              |
| M       | Swap the voice model between Drama 3 and S2.1 Pro (free)             |
| L       | Full lines (default, emotions hold) or streamed lines (word by word) |
| B       | Swap speech-to-text between Fish and Chrome's built-in one           |
| R       | Wipe everyone's memory                                               |
| Y       | Retake: same line again with a fresh voice take                      |


Wear headphones in hands-free mode, otherwise the mic hears the NPC.

## How it works

1. Your voice goes to Fish speech-to-text.
2. Claude (Sonnet 4.6 via OpenRouter) writes the reply in character, with acting notes in brackets.
3. Fish Drama 3 performs those notes over a websocket, and the audio streams straight to the browser.
4. Every conversation is shared with the other NPCs as gossip, so they bring up what you did.

Each reply costs roughly half a cent (Drama 3 is $10 per million characters), its 80% off for a month since 15th of Oct 2026.

## Make it yours

- **Characters, personalities and voices** live in `npcs.json`. Restart the server after editing it.
- **Find voices:** `python3 find_voices.py "pirate" "news anchor"` searches Fish's public voices, then paste an ID into `voice` in `npcs.json`. You can also make your own in Fish's Voice Design.
- **Change the writer model:** set `NPC_LLM` in `.env` to any OpenRouter model.

URL options:


| Option                       | What it does                                                                |
| ---------------------------- | --------------------------------------------------------------------------- |
| `?at=tony`                   | Spawn next to an NPC (tony, reyes, candy, dave)                             |
| `?dist=2.5`                  | Closer camera for filming                                                   |
| `?near=3&quiet=700&vad=0.02` | Hands-free range (metres), silence before sending (ms), and mic sensitivity |
| `?smooth=0`                  | Original flat low-poly look                                                 |




Want to make your own game like this? See [BUILD_YOUR_OWN.md](BUILD_YOUR_OWN.md) for the Blender setup, keys and a starter prompt.

## Credits

All 3D assets are CC0 (free to use, no credit required):

- Characters and props by [Quaternius](https://quaternius.com), and buildings from [Kenney](https://kenney.nl), all via [Poly Pizza](https://poly.pizza)
- Drunk Dave is the RobotExpressive model by Tomás Laulhé, from the [three.js](https://threejs.org) examples

Built with three.js, FastAPI, [Fish Audio](https://fish.audio/invite/?fpr=henryk) and Claude.