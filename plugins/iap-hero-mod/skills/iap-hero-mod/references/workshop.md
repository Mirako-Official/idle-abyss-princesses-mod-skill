# Testing in the game and uploading to the Steam Workshop

## Install for testing

Copy the `mod/` folder to `<userData>/mods/<mod id>/` (a real copy: the uploader refuses symlinked
folders) and restart the game.
- Windows `%APPDATA%\IdleAbyssPrincesses\mods\`
- macOS `~/Library/Application Support/IdleAbyssPrincesses/mods/`
- Linux `~/.config/IdleAbyssPrincesses/mods/`
- Steam Deck / Proton `~/.steam/steam/steamapps/compatdata/5335850/pfx/drive_c/users/steamuser/AppData/Roaming/IdleAbyssPrincesses/mods/`

Settings → Mods shows each mod as loaded / error / disabled with the reason and author hints (image
sizes that do not match the docs, bad JSON with line and column). The game log is
`<userData>/logs/main.log`. Launch option `--devtools` opens the console (needed for `i18n_dump.js`).
Code changes need a restart; developer mode (Settings → Mods → Author Tools) only hot-reloads data packs.

## In-game checklist (ask the player to look, or to send screenshots)

- [ ] hero picker: card, avatar crop on the face, bio, Mod tag
- [ ] left portrait smooth (not blocky); expressions switch when hit / casting / winning
- [ ] battle: chibi stands on its shadow, attack / cast / hurt play; skills cast; floating text readable
- [ ] resource bar readable; life bar and numbers sensible
- [ ] character page: doll, set bonus lines, equipment icons; hovering an item shows its card and icon
- [ ] skill page: names, descriptions with numbers, skill icons; talents with three routes
- [ ] every supported language: switch the game language and look again (untranslated Chinese shows
      as broken fragments)
- [ ] hero lab: all routes graded (balance.md)
- [ ] zero errors in Settings → Mods

## Upload (the player does this in the game)

Settings → Mods → the mod → **Upload to Workshop** (later: **Update on Workshop**). The uploader checks
before it uploads: valid manifest, the mod is loaded, content validation, a complete lab run for hero
mods, a preview image under 1 MB, no symlinks, under 100 MB, the rules checkbox, Steam running.
- Preview: `mod/preview.jpg` (make_preview.py). It is not uploaded as content.
- Title (≤ 80 characters) and an extra note; the names and descriptions of every language in
  `mod.json` are combined into the Workshop description automatically.
- Tags: type (Hero), Code (automatic for mods with scripts), languages, Balance (from the lab, cannot
  be edited), AI Art (tick it if any image model generated or edited art).
- Visibility: private (default) → test with a friend → public.
- The first upload writes `workshopId` into `mod.json`; keep it, so later uploads update the same item.
- Change notes: one line per change, plain.

## Description and credits

Keep each language's `description` in `mod.json` under 300 characters (the game cuts the rest) and
put the essentials in it: what the hero does, the routes in a few words, credits for the art (artist,
character owner, source), "fan work, not affiliated with …" for fan characters, and "can chat through
your own AI service" if `ai_chat.js` is included. The same credits go into `bio` and README.md.

## Workshop rules in short (the full text ships with the game)

No adult content; no ripped or unlicensed assets (fan art needs the artist's permission and credits);
code mods must not read or send player data, use the network (except chatting through IAP.ai, which
must be disclosed), touch files outside the mod folder and file area, run system commands, or
obfuscate code; tag AI-generated art; no impersonation, spam or misleading tags; never damage saves.
