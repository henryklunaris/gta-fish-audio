# Build your own

This whole game was built with [Claude Code](https://claude.com/claude-code) and the Blender MCP. Here's the setup.

## Accounts and keys


| What       | Where                                                                                                      | Used for                                                |
| ---------- | ---------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| Fish Audio | [Sign up](https://fish.audio/invite/?fpr=henryk), then the API section                                     | NPC voices (Drama 3) and speech-to-text                 |
| OpenRouter | [openrouter.ai](https://openrouter.ai)                                                                     | The model that writes the NPC lines                     |
| Poly Pizza | [poly.pizza](https://poly.pizza), sign in, then [poly.pizza/settings/api](https://poly.pizza/settings/api) | Free CC0 3D models (characters, cars, palms, buildings) |




## Blender MCP

1. Install [Blender](https://www.blender.org) and open it.
2. Install the add-on: `uvx mcp-for-blender install-addon`
3. Connect it to Claude Code: `claude mcp add blender uvx blender-mcp`
4. In Blender, open the MCP panel, click connect, and paste your Poly Pizza key.

Claude can now search Poly Pizza, import models, and export them as `.glb` files for the game.

## Things that will trip you up

- **Characters:** download the raw `.glb` from Poly Pizza instead of exporting through Blender, because the export stretches their ankles. Change outfit colours in code instead (see `recolor` in `npcs.json`). This might not always be an issue, but it was for me.
- **Robots with parts glued straight to bones** break on export. We used the three.js RobotExpressive model for Dave instead.
- **Cars, props and buildings** are fine to export through Blender.
- **If you use Claude Haiku**, turn reasoning off, or it spends all its tokens thinking and returns nothing.



## Starter prompt

If you'd like to re-create your own game.

Paste this into Claude Code in an empty folder:

```
Build a GTA-style browser game where NPCs talk back with AI voices.

- Python FastAPI server + a single index.html with three.js (load it from a CDN, no build step).
- A sunset Miami-style street with buildings, palm trees, streetlights and parked cars. Use the Blender MCP to find CC0 models on Poly Pizza and export them as .glb into assets/.
- A third-person player with WASD, sprint and a mouse-drag camera. Use rigged Poly Pizza characters loaded straight from their raw .glb (don't export characters through Blender) and recolour outfits in code.
- 4 NPCs defined in npcs.json, each with a name, personality and Fish Audio voice ID.
- Hold T to talk: record the mic, transcribe it with Fish Audio speech-to-text, and send it to an LLM on OpenRouter that replies in character in 1 or 2 short, funny sentences, with acting directions in square brackets like [leaning in, low and threatening].
- Voice the reply with Fish Audio TTS using the drama-3 model over their websocket, and stream the audio to the browser.
- Keep chat history per NPC, and share what the player says with the other NPCs as street gossip.
- Show subtitles, and play a gesture animation that matches the mood.
- Read FISH_API_KEY and OPENROUTER_API_KEY from .env using dotenv variables, never read the actual keys or bring them up to the user or yourself in the chat or terminal.

Look up the Fish Audio and OpenRouter API docs before writing code. Take screenshots of the game as you go to check it looks right (we might not have computer use enabled for Claude Code so it might not work, but we can try taking screenshots).
```

