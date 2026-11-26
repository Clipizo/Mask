# Mask

Cut a person or an object out of any video on your own computer, for free. Click the subject, Mask follows it through the video, and you get a mask or a video with a transparent background for your editor. No account, no subscription, no upload limits, and your videos never leave your computer.

Mask is a beginner-friendly kit for **SAM 2.1** (Segment Anything 2), the open video-segmentation models from Meta. It installs everything into one folder, and you use it in your browser.

> Mask is an unofficial kit made by Clipizo. It is not affiliated with or endorsed by Meta.
> The official SAM 2 source code is on GitHub: **[facebookresearch/sam2](https://github.com/facebookresearch/sam2)**.

## What you need

- **Free disk space: about 3 GB.** The programs take about 1 GB. The AI models take 0.4 to 1.5 GB, depending on your computer and the qualities you use (see [The AI models](#the-ai-models)). Leave room for your results too: a few minutes of ProRes video can take several GB.
- **A computer:** a Windows 10 or 11 PC, a Mac with Apple Silicon (M1 or newer), or a Linux PC. Intel Macs and Windows on ARM aren't supported.
- **A graphics card (optional):** on Windows, Mask uses any graphics card that runs DirectX 12 (NVIDIA, AMD or Intel); on a Mac, it uses the Mac's GPU. Without one (and on Linux), it runs on the processor: it works, but tracking is much slower.
- **An internet connection** for the install (about 300 MB) and the first download of the models.

## Installation

### The easiest way: let your AI assistant guide you

Paste this into ChatGPT, Claude, Gemini or Copilot:

```text
Help me install and use Mask: https://github.com/Clipizo/Mask
Read its file "Mask AI Guide.md" first, then guide me one step at a time.
```

If your AI can't open links, download [`Mask AI Guide.md`](Mask%20AI%20Guide.md) and attach it to the chat instead.

Using an AI agent that can run commands (Claude Code, OpenAI Codex, Gemini CLI, Cursor, VS Code with Copilot)? Ask it, for example, *"Download https://github.com/Clipizo/Mask to C:\Mask and install it by following its SKILL.md"* (on a Mac or Linux, say `~/Mask`). If you already have the Mask folder, open it in the agent instead. The agent follows `AGENTS.md` and `SKILL.md`.

### Install it yourself

You don't need Python or anything else first: the installer gets everything Mask needs and puts it in the Mask folder. It takes 2 to 15 minutes, depending on your internet connection.

**How it works:** copy a command, paste it into the window, and press Enter. Wait until the window is ready for the next one (Windows: a new line starting with `PS`; Mac and Linux: a new line ending with `%` or `$`). Many commands print nothing when they work, and that's normal.

#### Windows 10 or 11

**Step 1. Open PowerShell.** Press the Windows key, type `PowerShell`, and press Enter. To paste in it, right-click or press Ctrl+V.

**Step 2. Download Mask**
```powershell
Invoke-WebRequest "https://github.com/Clipizo/Mask/archive/refs/heads/main.zip" -OutFile "$env:TEMP\Mask.zip" -UseBasicParsing
```

**Step 3. Unzip it**
```powershell
Expand-Archive "$env:TEMP\Mask.zip" -DestinationPath "C:\" -Force
```

**Step 4. Rename the folder to `C:\Mask`**
```powershell
Rename-Item "C:\Mask-main" "Mask"
```

**Step 5. Go into the folder**
```powershell
cd C:\Mask
```

**Step 6. Install Mask**
```powershell
./install-windows.bat
```
It works through 5 steps. When it asks *"Get the AI models now?"*, press Enter. It's done when it says **Mask is installed!**, then *"Press any key to continue"*: press a key.

**Step 7. Start Mask**
```powershell
./mask
```
Mask opens in your browser. Keep the PowerShell window open while you use it.

**If a step shows red text:**
- **Step 2:** check your internet connection and paste the command again.
- **Step 4** says the file *already exists*: you already have a `C:\Mask` folder. Keep it under another name with the command below, then do step 4 again.
  ```powershell
  Rename-Item "C:\Mask" "Mask-old"
  ```
- **Step 6:** the installer explains the problem in plain words. Paste the command again: it continues where it stopped. Still stuck? Give the text in the window, or the file `install-log.txt` in `C:\Mask`, to your AI assistant.

Prefer clicking? Click the green **Code** button on this page > **Download ZIP**. Right-click the ZIP > **Extract All...**, extract it to `C:\` and rename the folder to `C:\Mask`. Then double-click `install-windows.bat` to install, and `mask.bat` to start. If Windows says *"Windows protected your PC"*, click **More info** > **Run anyway**.

#### Mac (Apple Silicon)

**Step 1. Open Terminal.** Press Cmd+Space, type `Terminal`, and press Enter.

**Step 2. Go to your home folder**
```bash
cd ~
```

**Step 3. Download Mask**
```bash
curl -L -o Mask.tar.gz https://github.com/Clipizo/Mask/archive/refs/heads/main.tar.gz
```

**Step 4. Unpack it**
```bash
tar -xzf Mask.tar.gz
```

**Step 5. Rename the folder to `Mask`**
```bash
mv Mask-main Mask
```

**Step 6. Go into the folder**
```bash
cd ~/Mask
```

**Step 7. Install Mask** (it works through 5 steps; when it asks *"Get the AI models now?"*, press Enter; it's done when it says **Mask is installed!**)
```bash
bash install.sh
```

**Step 8. Start Mask**
```bash
./mask
```
Mask opens in your browser. Keep the Terminal window open while you use it.

Installed Mask before? Then before step 5, keep the old folder under another name with `mv ~/Mask ~/Mask-old`.

#### Linux

The same steps as on a Mac, in a terminal (on Ubuntu, press Ctrl+Alt+T to open one). If step 3 says `curl: command not found`, use this instead:
```bash
wget -O Mask.tar.gz https://github.com/Clipizo/Mask/archive/refs/heads/main.tar.gz
```
You don't need administrator rights (`sudo`) for any step. On Linux, Mask runs on the processor.

**To start it again later:**

- **Windows:** double-click `mask.bat` in the `C:\Mask` folder.
- **Mac and Linux:** in Terminal, run `cd ~/Mask` and then `./mask`.

## Using Mask

Start Mask (double-click `mask.bat` on Windows, or run `./mask` in the Mask folder) and it opens in your browser:

1. **Open a video.** Drop it on the page, or paste its path into the box below it and press Enter (better for big videos: nothing is copied).
2. **Click the subject.** With *A click adds: Keep*, each click adds a point on what you want; with *Cut*, a point on what you don't want. The selection shows in lime right away. *Undo point* and *Clear points* fix mistakes.
3. **Set In and Out** if you only need part of the video: go to a frame and click *Set In* or *Set Out*. *Whole video* resets them.
4. **Track.** *Forward* follows the subject from the frame you clicked to Out; *Backward* follows it back to In. *Stop tracking* stops it; the frames it finished keep their masks.
5. **Check it.** Drag the frame slider, or use the ◀ ▶ buttons. *Overlay*, *Cutout*, *Mask* and *Original* show the result in different ways. If the mask goes wrong on a frame, click the subject there: that frame becomes another keyframe, and tracking again follows the subject from each keyframe to the next.
6. **Export** the frames between In and Out (see [What you get](#what-you-get)), then click the file under *Download*. The files are also in the **`output`** folder.

*Quality* picks the model for your clicks: **Faster**, **Balanced** (the default) or **Better** (the most precise edges; it needs the graphics card or the Mac's GPU). Your keyframes, In and Out are saved: open the same video file by its path later and you continue where you left off.

It runs only on your computer. Keep the window that started it open while you use it; close it to stop Mask.

## What you get

For `my-video.mp4`, Mask keeps everything in `output/my-video/`: the mask of every frame in `masks/`, and your exports in `exports/`, named after the In and Out frames (for example `my-video-000120-000480-alpha.mov`). An export never replaces an earlier one: a second export of the same frames gets a number (`-2`, `-3`...).

| Export | What it is | Use it for |
|---|---|---|
| **Video with transparency (MOV, ProRes 4444)** | The subject on a transparent background, full quality | DaVinci Resolve, Premiere Pro, After Effects, Final Cut Pro |
| **Video with transparency (WebM)** | The same, small, for the web | Web pages and browsers (Chrome, Edge, Firefox) |
| **Matte video (MP4)** | Black and white: white is the subject | A luma (track) matte in your editor, on top of the original video |
| **Mask images (PNG)** | The same matte as one PNG per frame, in a ZIP | Compositing and VFX programs |
| **Cutout images (PNG with transparency)** | The subject on a transparent background, one PNG per frame, in a ZIP | Image editors, animations, thumbnails |

The exported frames are exactly the video's frames, so a matte lines up with the original when both start at the same frame.

## The AI models

Mask uses Meta's **SAM 2.1** models, converted for ONNX Runtime by Clipizo. **You don't need to download them yourself:** the installer gets Balanced and tracking, and Mask gets another quality the first time you pick it. They stay in the `models` folder, and an interrupted download continues where it stopped.

| Quality | Windows with a graphics card | Mac, and any computer without a graphics card |
|---|---|---|
| Tracking (always needed) | `sam2_track_small_fp16.onnx`, 105 MB | `sam2_track_small_coreml.onnx`, 227 MB |
| Faster | `sam2_image_tiny_fp16.onnx`, 65 MB | `sam2_image_tiny_coreml.onnx`, 157 MB |
| Balanced | `sam2_image_small_fp16.onnx`, 79 MB | `sam2_image_small_coreml.onnx`, 189 MB |
| Better | `sam2_image_large_fp16.onnx`, 437 MB | `sam2_image_large_coreml.onnx`, 910 MB |

On Windows with a graphics card, the installer also gets the processor versions (the right column) of tracking and Balanced, in case the card can't run them. `./mask download all` gets every quality, for example before you go offline. Better runs only on a graphics card or a Mac's GPU, because on the processor it takes about half a minute per click.

They download from Clipizo's download address, `https://downloads.clipizo.com/mask/models/v1/` (stored on Cloudflare; the folder also has their license and a list of the files), and Mask checks every file before using it.

**Have Maskizo?** If Clipizo's Maskizo plugin for DaVinci Resolve is installed on the computer, Mask copies the models from it instead of downloading them.

**To copy the models from another computer** (for example, if your network blocks the download), copy the `models` folder to a USB stick, then run `./mask download all --from E:\models` (with your own path). It copies the files this computer needs and tells you which ones the folder doesn't have.

## Commands

Open PowerShell (Windows) or Terminal (Mac and Linux), go into the Mask folder as in the install steps, and type one of these. The commands are the same on every system.

| What | Command |
|---|---|
| Open Mask in the browser | `./mask` |
| Open it with a video already loaded | `./mask --video "D:\Videos\my video.mp4"` |
| Check the setup | `./mask check` |
| Get the models of every quality | `./mask download all` |
| Copy the models from a folder | `./mask download all --from E:\models` |
| Every option | `./mask help` |

## What is inside

| File or folder | Contents |
|---|---|
| `install-windows.bat`, `install.sh` | The installers. Run them again at any time to repair the install. |
| `mask.bat`, `mask.sh` | Start Mask. On Mac and Linux the installer also adds a `mask` shortcut, so `./mask` works everywhere. |
| `Mask AI Guide.md` | Everything an AI assistant needs to help you, step by step, including troubleshooting. |
| `AGENTS.md`, `SKILL.md` | Instructions for AI agents. `CLAUDE.md` and `GEMINI.md` point to them. |
| `app/` | The Mask program. |
| `tests/` | Mask's own tests. |
| `licenses/` | The AI models' license (Apache 2.0, from Meta) and the list of model files. |
| `output/` | Your masks and exports. |
| `envs/`, `models/`, `.tools/` | Created by the installer: Python, the libraries and the AI models. |

**To uninstall,** delete the Mask folder. Nothing else is installed on your computer, except Microsoft's free Visual C++ component on a Windows PC that didn't have it yet (the installer asks first; other programs use it too, so leave it).

## Respect people's rights

Mask videos you made, or have the right to use. Cutting people out of videos and putting them somewhere else can mislead viewers, and using someone's image without their consent can be illegal in some places.

## License and credits

Mask is free of charge, under the Clipizo product license in `LICENSE.txt`. Use it and what you make with it in your own projects, personal or commercial, including client work and monetized videos. Please don't re-upload or redistribute the kit's files; link to this page instead.

The AI models are made by Meta and released under the Apache 2.0 license: [SAM 2](https://github.com/facebookresearch/sam2). Mask downloads converted copies of them, and the open-source tools it uses, from their sources. See `THIRD-PARTY-NOTICES.md`.
