# Mask

This folder is **Mask**, a kit that runs Meta's open SAM 2.1 models on the user's computer: it cuts a person or an object out of a video, in a page in the browser, and exports masks, mattes and videos with transparency.

When the user asks to install or fix Mask, or to mask, cut out, rotoscope or remove the background of a video, **read `SKILL.md` and follow it**. It points you to `Mask AI Guide.md`, the full reference.

Ground rules:

- Run Mask through its launcher, `./mask` (on Windows it runs `mask.bat`, on Mac and Linux `mask.sh`). Install or repair it only with `install-windows.bat` or `install.sh`; don't install packages yourself.
- Keep the user's results in `output/`. Don't delete or overwrite their files without asking.
- Leave the kit files unchanged unless the user asks: `app/`, the installers, the docs, `SKILL.md`.
