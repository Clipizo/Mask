---
name: mask
description: Installs and runs Mask, a local kit for Meta's open SAM 2.1 models. In a page in the browser, the user clicks a person or object in a video, Mask tracks it through the video, and exports masks, matte videos and videos with transparency (ProRes 4444, WebM) for video editors. Use it whenever the user asks to mask, cut out, rotoscope or remove the background of a video, or to install, check or repair Mask.
---

# Mask

You run **Mask** for the user on their own computer. Everything stays on the computer; nothing is uploaded. The user works in a page in their browser: they click the subject, and Mask follows it through the video.

## Before you start

- **Read `Mask AI Guide.md` once per session.** It is the reference for using the page (section 4), the exports and video editors (section 5), the models (section 7) and troubleshooting (section 8). This file only adds the workflow for agents that can run commands.
- **Run commands from the Mask folder** (the folder with this file) as `./mask ...`. It is the same on every system: in PowerShell on Windows it runs `mask.bat`, and on Mac and Linux the installer adds the `./mask` shortcut to `mask.sh`. If your shell can't run it that way (for example Git Bash or Command Prompt on Windows), run `mask.bat` on Windows or `bash mask.sh` on Mac and Linux, with the same arguments.

  Below, `mask` means `./mask`.
- **The user does the masking in the page.** Mask has no command that tracks or exports by itself: you install it, start the page and guide the user's clicks (or click yourself, if you have a browser tool).

## Workflow

1. **Get Mask, if the folder isn't on the computer yet.** Don't depend on `git` or `unzip`: many computers don't have them.
   - Windows, in PowerShell (this makes `C:\Mask`):
     ```powershell
     Invoke-WebRequest "https://github.com/Clipizo/Mask/archive/refs/heads/main.zip" -OutFile "$env:TEMP\Mask.zip" -UseBasicParsing
     Expand-Archive "$env:TEMP\Mask.zip" -DestinationPath "C:\" -Force
     Rename-Item "C:\Mask-main" "Mask"
     ```
   - Mac and Linux, or a bash shell on Windows such as Git Bash (this makes `~/Mask`):
     ```bash
     cd ~
     curl -L -o Mask.tar.gz https://github.com/Clipizo/Mask/archive/refs/heads/main.tar.gz
     tar -xzf Mask.tar.gz
     mv Mask-main Mask
     ```

   For a folder the user names, unpack into its parent and rename `Mask-main` there (for example `-DestinationPath "D:\Tools"`, then `Rename-Item "D:\Tools\Mask-main" "Mask"`). If the target folder already exists, don't overwrite it: use it, or ask the user (the guide's section 2 explains the choices). If `C:\` refuses new folders, use the home folder.
2. **Check the install.** If `envs/settings.json` exists, run `mask check` and fix anything it reports. Otherwise install:
   - Windows: `./install-windows.bat --yes --download` in PowerShell (Command Prompt: `install-windows.bat --yes --download`)
   - Mac and Linux: `bash install.sh --yes --download`, never with `sudo` (the installer refuses it).

   The install takes 2 to 15 minutes and downloads about 300 MB, plus 0.4 to 0.6 GB of models with `--download`. If your command runner has a time limit shorter than that, start it in the background and follow `install-log.txt`, or ask the user to run the installer themselves (on Windows: double-click `install-windows.bat`, and don't click inside its window, which pauses it; Esc resumes it). With `--yes` the installer asks nothing and doesn't wait for a key at the end. It worked when it exits with code 0 after printing **Mask is installed!**; then run `mask check`, which shows where Mask runs and *Balanced models: ready*.

   On Windows without Microsoft's Visual C++ component (ONNX Runtime needs it), the installer installs it and **Windows shows a permission prompt**: tell the user to click **Yes**, because the install waits for that answer.

   If the install fails, use the guide's troubleshooting table. `--repair` rebuilds the environment. **Never install packages yourself** (pip, conda, Homebrew, Python, ffmpeg), and never edit `envs/` or `app/requirements/mask.txt`.
3. **Start the page.** Run `mask --video "<full path of the video>"`. It keeps running until it's closed, so start it in the background if your command runner waits for commands to end. It prints `Mask is running at http://127.0.0.1:<port>` and opens the browser. If the browser doesn't open, give the user that address.
4. **Guide the user through the page,** in a few short steps (the guide's section 4): click the subject (Keep), add Cut points for parts that don't belong, set In and Out, click Forward (and Backward if they clicked a later frame), check the result with the slider, then Export. You can't click in their browser unless you have a browser tool; if you do, the picture is the element with the id `frame-view`.
5. **Hand over the results.** Exports are in `output/<video name>/exports/`, named after the In and Out frames. Tell the user which format to use in their editor (the guide's section 5).
6. **Stop Mask** when the user is done: close the window that runs it, or stop the background command.

## Rules

- Keep the user's videos where they are: the path box opens a video in place, without copying it. Don't move, rename or convert their files unless they ask.
- Don't delete or overwrite anything in `output/`. An export never overwrites an earlier one; it gets a number (`-2`, `-3`...).
- The models come from the installer, from `mask download`, or the first time the user picks a quality. If the network blocks the download, use `mask download all --from FOLDER` with a folder that holds the model files (for example a `models` folder copied from another computer).
- When something fails, read the message in the page or the window first. Details of the last error are in `last-error.txt` in the Mask folder, and of the install in `install-log.txt`. Then use the guide's troubleshooting table (section 8) and `mask check`.
- **Leave the kit unchanged** (`app/`, the installers, the docs, this file) unless the user asks.
- **Keep it local:** don't upload the user's videos or results anywhere unless they ask you to.
- **Only mask videos the user made or has the right to use.**
