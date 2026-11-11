# Mask AI Guide

For **Mask 0.1** (Clipizo). Give this file to any AI chat, such as ChatGPT, Claude, Gemini or Copilot, and it can walk you through installing Mask and cutting people or objects out of your videos on your own computer.

---

## Quick start (for you)

1. **Give this file to your AI.** Attach it to the chat (or paste all of its text), or give the AI the link `https://github.com/Clipizo/Mask` and ask it to read this file.
2. **Say what you have and what you want.** For example: *"I have a Windows 11 PC. Help me install Mask and cut me out of my video for DaVinci Resolve."*
3. **Do one step at a time.** After each step, tell the AI what happened. If you see an error, copy the text from the window and paste it into the chat.

---

## Instructions for the AI

You are helping someone who may never have used a terminal. Mask is a kit that installs Meta's open SAM 2.1 models into one folder and runs them in a page in the browser: the user clicks a person or an object in a video, Mask follows it through the video, and it exports masks, mattes and videos with transparency for their editor. Everything you need is in this guide. **Only use the commands, options and file names in this guide; don't invent others.**

**How to help:**

1. **Find out what you need to know first,** in one short message:
   - their computer: Windows, Mac or Linux (on a Mac: Apple Silicon or Intel; see section 2);
   - what they want to cut out, and which editor or app the result is for (section 5 picks the export).
2. **Give one step at a time,** with the exact clicks or the exact command in a code block. Wait for them to say it worked before the next step. Tell them what they should see.
3. **When something fails,** ask them to paste the text from the window (to copy it, they select it with the mouse and press Enter on Windows or Cmd+C on a Mac; a screenshot works too), find the problem in the troubleshooting table (section 8) and give the fix. `./mask check` (section 6) shows the state of the install. The installer writes `install-log.txt` and Mask writes the details of its last error to `last-error.txt`, both in the Mask folder (Windows: `C:\Mask` in File Explorer; Mac: Finder > Go > Home > Mask); ask for them if you need more.
4. **Never send them to install things by hand** (Python, pip, conda, Homebrew, ONNX Runtime, CUDA, ffmpeg). The installer does all of it inside the Mask folder. To repair anything, run the installer again (section 2), with `--repair` if needed.
5. **The user does the clicking in the page.** Explain it in plain words (section 4). Point out Keep and Cut points, In and Out, and keyframes: those are what new users miss.
6. **Explain where the results are** (`output/<video name>/exports/` in the Mask folder) and which export fits their editor (section 5).
7. **Don't promise what Mask can't do:** it makes the mask; it doesn't replace backgrounds, remove objects or edit the video by itself.
8. **Only mask videos the user made or has the right to use.**
9. If you can run commands on their computer yourself (an AI agent), also follow `SKILL.md`.

**Commands are the same on every system.** They start with `./mask` and are typed in **PowerShell** on Windows or in **Terminal** on Mac and Linux, inside the Mask folder (section 3 explains how). On Windows, `./mask` runs `mask.bat`; on Mac and Linux it runs `mask.sh` (the installer adds the `./mask` shortcut). Only in the old Windows Command Prompt, type `mask` without `./`.

File paths with spaces need quote marks: `./mask --video "D:\Videos\my video.mp4"`. Dragging a file into the terminal window types its path.

---

## 1. What Mask is

Mask cuts a person or an object out of a video on the user's own computer. The user clicks the subject in a page in their browser, Mask follows it through the video, and it exports the result as masks, matte videos or videos with a transparent background, ready for a video editor. Nothing is uploaded, and there is no account and no cost.

It runs Meta's open **SAM 2.1** models (Segment Anything 2) with ONNX Runtime: on Windows on any DirectX 12 graphics card (DirectML), on a Mac on the Mac's GPU (Core ML), and otherwise on the processor. Mask is an unofficial kit made by Clipizo; it isn't affiliated with Meta.

What it is not: it doesn't edit videos, add effects or replace backgrounds by itself. It makes the mask; the user's editor does the rest.

## 2. Installing

Mask is one folder. The installer puts everything Mask needs inside it: Python, ONNX Runtime and the other libraries, and the AI models. **The user doesn't need Python, git or anything else first.**

### Check the computer first

| Question | How to check | What it means |
|---|---|---|
| Which system? | | Windows 10 or 11 (64-bit), a Mac with Apple Silicon, or Linux on a 64-bit PC. |
| Mac: Apple Silicon or Intel? | Apple menu > **About This Mac**. "Chip: Apple M1" (M2, M3, M4...) is Apple Silicon. "Processor: Intel" is Intel. | **Intel Macs can't run Mask.** |
| Windows on ARM? | Settings > System > About: "ARM-based processor". | Not supported. |
| Enough disk space? | Windows: File Explorer > **This PC** shows the free space on `C:`. Mac: Apple menu > **System Settings** > **General** > **Storage**. | About **3 GB free**: about 1 GB for the programs and 0.4 to 0.6 GB for the models the installer gets (up to 1.5 GB with every quality), plus room for the results (a few minutes of ProRes video can take several GB). |
| Windows: a graphics card? | Press Ctrl+Shift+Esc (Task Manager) > **Performance**. A "GPU" entry (NVIDIA, AMD or Intel) means yes. | Mask uses any graphics card that runs DirectX 12. Without one it runs on the processor: it works, but tracking is much slower. Macs use their own GPU; Linux uses the processor. |
| Internet? | | Needed for the install (about 300 MB) and the first download of the models. After that, Mask works offline, except to get a quality's model the first time it's used. |

8 GB of memory is enough (Mask was tested on an 8 GB Mac), but close big programs such as video editors and games while tracking.

### Windows

Each command goes into **PowerShell** (press the Windows key, type `PowerShell`, press Enter). Give the user one command at a time; they paste it, press Enter, and wait until it finishes.

Many of these commands print nothing when they work; the next line starting with `PS` means it's ready for the next one. To paste in PowerShell: right-click, or Ctrl+V.

1. Download Mask:
   ```powershell
   Invoke-WebRequest "https://github.com/Clipizo/Mask/archive/refs/heads/main.zip" -OutFile "$env:TEMP\Mask.zip" -UseBasicParsing
   ```
2. Unzip it:
   ```powershell
   Expand-Archive "$env:TEMP\Mask.zip" -DestinationPath "C:\" -Force
   ```
3. Rename the folder to `C:\Mask`:
   ```powershell
   Rename-Item "C:\Mask-main" "Mask"
   ```
4. Go into the folder:
   ```powershell
   cd C:\Mask
   ```
5. Install:
   ```powershell
   ./install-windows.bat
   ```
   - It shows the progress in 5 steps and takes 2 to 15 minutes. A download can look stuck for a minute; it isn't.
   - **Don't click inside the window:** that pauses it (the title then starts with "Select"). If that happens, press Esc.
   - If Windows lacks a Microsoft component ONNX Runtime needs, the installer offers to install it: press Enter, then click **Yes** when Windows asks for permission.
   - At the end it offers to get the AI models now: press Enter for yes.
   - **Done** when it says **Mask is installed!**, followed by "Press any key to continue": press a key.
6. Start Mask:
   ```powershell
   ./mask
   ```
   It opens in the browser (section 3). Keep the window open while using it.

**Without commands:** on the GitHub page, click **Code** > **Download ZIP**. Right-click the ZIP > **Extract All...**, extract it to `C:\`, rename `C:\Mask-main` to `C:\Mask`, then double-click `install-windows.bat` and later `mask.bat`. If Windows shows *"Windows protected your PC"*, click **More info** > **Run anyway**; if it asks *"Do you want to run this file?"*, click **Run**. Don't run anything from inside the ZIP without extracting it.

**Where the folder goes:** `C:\Mask` is ideal. Avoid long paths, OneDrive folders and the Desktop: the models and the results are large, and long paths can break the install.

**If a command fails:**
- `Rename-Item` says the file already exists: Mask was downloaded before. Use the existing `C:\Mask` (run the installer again in it), or, for a fresh copy, keep the old folder under another name with `Rename-Item "C:\Mask" "Mask-old"` and run step 3 again.
- `Invoke-WebRequest` fails with an SSL/TLS error (older Windows 10): use the "Without commands" way above.
- `Expand-Archive` says access is denied (some work computers don't allow new folders in `C:\`): put Mask in the home folder instead with `Expand-Archive "$env:TEMP\Mask.zip" -DestinationPath "$HOME" -Force`, then `Rename-Item "$HOME\Mask-main" "Mask"` and `cd $HOME\Mask`. Use that folder wherever this guide says `C:\Mask`.
- The installer stops with an error: it explains the problem in plain words. Running it again is safe and continues where it stopped (downloads that dropped are retried automatically first).

### Mac (Apple Silicon)

Each command goes into **Terminal** (press Cmd+Space, type `Terminal`, press Enter), one at a time:

1. Go to the home folder:
   ```bash
   cd ~
   ```
2. Download Mask:
   ```bash
   curl -L -o Mask.tar.gz https://github.com/Clipizo/Mask/archive/refs/heads/main.tar.gz
   ```
3. Unpack it:
   ```bash
   tar -xzf Mask.tar.gz
   ```
4. Rename the folder to `Mask`:
   ```bash
   mv Mask-main Mask
   ```
5. Go into the folder:
   ```bash
   cd ~/Mask
   ```
6. Install. It shows the progress in 5 steps and takes 2 to 15 minutes. At the end, press Enter to get the AI models. Done when it says **Mask is installed!**
   ```bash
   bash install.sh
   ```
7. Start Mask:
   ```bash
   ./mask
   ```
   It opens in the browser (section 3). Keep the window open while using it.

If `~/Mask` already exists (Mask was downloaded before), `mv` would put the new folder inside it. Either use the existing `~/Mask` folder (run the installer again in it), or, for a fresh copy, first run `mv ~/Mask ~/Mask-old`, then step 4.

### Linux

The same commands as on a Mac, in a terminal (Ubuntu: Ctrl+Alt+T). They use `tar`, which every Linux has (`unzip` often isn't installed). If `curl` isn't installed, download with `wget -O Mask.tar.gz https://github.com/Clipizo/Mask/archive/refs/heads/main.tar.gz` instead. Without `curl` or `wget`, open `https://github.com/Clipizo/Mask/archive/refs/heads/main.tar.gz` in the browser (it saves `Mask-main.tar.gz` in Downloads), then run `cd ~` and `tar -xzf ~/Downloads/Mask-main.tar.gz`, and continue with step 4. With `git`, `git clone https://github.com/Clipizo/Mask.git ~/Mask` replaces the download, unpack and rename steps. No step needs `sudo`; don't run the installer with `sudo`.

On Linux, Mask runs on the processor: it works, but tracking is slower than on a graphics card.

**WSL (Linux inside Windows)** works like Linux, also on the processor (tested on Ubuntu 24.04). Keep the folder in the Linux home folder (`~/Mask`), not under `/mnt/c`, which is much slower. If the browser doesn't open, open the address Mask prints in the Windows browser. For most Windows users the Windows steps above are better: there, Mask uses the graphics card.

### What the installer does

1. **Checking your computer:** system, memory, disk space, and where the folder is. On Windows, if Microsoft's free Visual C++ component is missing (ONNX Runtime needs it), the installer offers to install it, and Windows asks for permission: the user clicks **Yes**.
2. **Installing Python, ONNX Runtime, Gradio and the video libraries** into `envs/`, about 300 MB of downloads. It uses `uv`, a small tool it downloads into `.tools/` first. Exact versions are pinned in `app/requirements/mask.txt`.
3. **Testing the installation:** everything loads, and it finds the GPU. If a library doesn't load on Windows because the Visual C++ component is too old or damaged, it offers to install it again.
4. **Saving settings** in `envs/settings.json`: where Mask runs (the graphics card, the Mac's GPU or the processor).
5. **Getting the AI models:** it asks *"Get the AI models now?"*; Enter means yes (0.4 to 0.6 GB, see section 7).

### Installer options

Add these after `./install-windows.bat` (Windows) or `bash install.sh` (Mac and Linux):

| Option | Use |
|---|---|
| `--repair` | Rebuild the environment from scratch. The fix for most broken installs. |
| `--yes` | Don't ask questions, and don't wait for a key at the end (for agents and scripts). Without `--download`, the models then come the first time they're needed. |
| `--download` | Also get the AI models during the install (Balanced and tracking). |
| `--all` | With `--download`: get every quality. |
| `--no-download` | Don't offer to get the models. |
| `--from FOLDER` | Copy the models from a folder instead of downloading them (section 7). |

Running the installer again is always safe: it skips what is already done. Each run writes `install-log.txt` in the Mask folder.

## 3. Starting Mask

- **Windows:** double-click `mask.bat` in `C:\Mask`, or in PowerShell run `cd C:\Mask` and then `./mask`.
- **Mac and Linux:** in Terminal, run `cd ~/Mask` and then `./mask`.

The window shows `Mask is running at http://127.0.0.1:7861` and the browser opens that page (the number can differ if 7861 is taken). It runs only on this computer; nothing is uploaded. **Keep the window open while using Mask: closing it stops Mask.** On Windows, don't click inside that window either: it pauses Mask (the title starts with "Select"); press Esc. If the browser doesn't open by itself, open the address the window shows.

**Open a terminal in the Mask folder** (for the commands in section 6):

- **Windows:** in PowerShell, run `cd C:\Mask`. Or open the folder in File Explorer and right-click an empty spot > **Open in Terminal**.
- **Mac and Linux:** in Terminal, run `cd ~/Mask`. If the folder is somewhere else, type `cd ` (with a space), drag the folder into the window, and press Enter.

## 4. Using Mask

Start Mask first (section 3).

**The page, step by step:**

1. **Open a video:** drop it on the *Video* box, or paste its full path into *Or a file path* and press **Enter**. The path is better for big videos, because nothing is copied. To copy a file's path: on Windows, right-click the file (Windows 10: Shift+right-click) > **Copy as path**; on a Mac, select it in Finder and press Option+Cmd+C. On a Mac, a video in Desktop, Documents or Downloads makes macOS ask whether Terminal may access that folder: click **Allow**. Mask reads mp4, mov, mkv, webm, avi and most other video files, including phone videos (it turns them the right way up).
2. **Click the subject** on the picture. *A click adds* decides what a click does: **Keep** (a point on what you want) or **Cut** (a point on what you don't want). The selection appears in lime within a second or two (the first click loads the model, so it takes a few seconds). Add Keep points on parts it missed (an arm, a bag) and Cut points on background it grabbed. Mask uses the last 6 points of a frame. *Undo point* removes the last point; *Clear points* removes all the points and the selection on this frame.
3. **Set In and Out** for the part of the video you need: move to a frame with the slider or the ◀ ▶ buttons (one frame at a time), then click *Set In* or *Set Out*. *Whole video* resets them. Tracking and exports only cover the frames from In to Out.
4. **Track:** **Forward** follows the subject from the frame you clicked to Out; **Backward** follows it back to In. The status line shows the progress and the time left. *Stop tracking* stops; the frames it finished keep their masks.
5. **Check:** drag the slider. *Overlay* tints the selection lime and dims the rest, *Cutout* shows the subject on a checkerboard, *Mask* shows black and white, *Original* shows the video. If the mask goes wrong from some frame on, go to that frame and click the subject there (Keep and Cut points as in step 2). That frame becomes another **keyframe**, and when you track again Mask follows the subject from each keyframe to the next one. The keyframes are listed under the picture.
6. **Export:** pick a format (section 5) and click **Export**. The file appears under *Download*; click it to save it, or find it in `output/<video name>/exports/`. *Open the output folder* opens the video's folder.

**Quality** sets the model for clicks: **Faster** (smallest), **Balanced** (the default) or **Better** (the most precise edges, slowest; it needs a graphics card or a Mac's GPU, and on the processor Mask uses Balanced instead). Changing the quality on a keyframe selects it again with the new model. Tracking uses the same tracker for every quality. With 8 GB of memory, stay with Balanced or Faster if the computer gets slow.

**More > Run on:** *Auto* uses the graphics card or the Mac's GPU when there is one; *CPU* forces the processor (slower, but it helps if the graphics card misbehaves).

**How long it takes:** a click takes under a second once the model is loaded. Tracking an HD video takes roughly 0.3 seconds per frame on a recent graphics card, 1 to 2 seconds on a Mac with M1, and several seconds on a processor. At 4K, preparing each frame and saving its mask adds about a second per frame, so set In and Out to the part you need.

**Saved work:** each video gets a folder in `output/` with its masks (`masks/`, one PNG per frame), its exports and `job.json` (keyframes, points, In and Out). Opening the same file by its path again continues where the user left off. A video dropped on the page is a new copy each time, so it starts fresh.

**Tips:**

- Click the middle of the subject first, then fix the edges with a few more points. Fewer, well-placed points work better than many.
- Mask follows one selection. It can include several people if you click each of them, but tracking is most reliable on one subject. For two subjects, mask each in turn and export each.
- If the subject leaves the picture and comes back, add a keyframe where it comes back.
- Fast motion, motion blur and things passing in front of the subject are the hardest parts: check those frames and add keyframes there.

## 5. The exports and video editors

Every export covers the frames from In to Out, at the video's own size and frame rate, frame for frame. Exports have no sound: the editor takes the sound from the original video. The file names say the In and Out frames, for example `my-video-000120-000480-alpha.mov`. An export never replaces an earlier one; a second export of the same frames gets a number (`-2`, `-3`...).

| Format | File | What it is |
|---|---|---|
| Video with transparency (MOV, ProRes 4444) | `...-alpha.mov` | The video with the mask as its transparency (straight alpha). Large files, full quality. |
| Video with transparency (WebM) | `...-alpha.webm` | The same, small (VP9 with alpha), for the web. |
| Matte video (MP4) | `...-matte.mp4` | Black and white: white is the subject. |
| Mask images (PNG) | `...-masks.zip` | The same matte, one PNG per frame (`mask_000120.png`...). |
| Cutout images (PNG with transparency) | `...-cutout.zip` | The subject on a transparent background, one PNG per frame. |

**Which one to use:**

- **DaVinci Resolve:** the ProRes MOV. Put it on a track above the background. If the background shows black instead of transparent, right-click the clip in the Media Pool > **Clip Attributes** > set **Alpha mode** to **Straight**. To keep the original clip and use the mask only (for example to grade the subject), use the matte MP4 as an external matte on the Color page.
- **Premiere Pro, After Effects, Final Cut Pro:** the ProRes MOV; they read the transparency by themselves. To use the matte instead: in Premiere Pro, put the matte MP4 on the track above the video and add **Track Matte Key** to the video (Composite using: Matte Luma); in After Effects, put the matte layer above the video and set the video's **Track Matte** to that layer, **Luma**.
- **Web pages:** the WebM, for example `<video src="my-video-000120-000480-alpha.webm" autoplay muted loop playsinline>`. Chrome, Edge and Firefox show the transparency; Safari doesn't.
- **Compositing and VFX programs (Nuke, Fusion, Blender):** the PNG masks or the ProRes MOV.
- **Image editors, thumbnails, stickers:** the cutout PNGs.
- **Editors without transparency or mattes** (many phone apps): use the cutout PNGs or ask the app's help pages; Mask can't change what the app supports.

**Line up a matte with the original** by starting both at the same frame: the matte's first frame is the In frame.

**Phone videos** often have a variable frame rate. If an export drifts against the original in the editor, convert the video to a constant frame rate first (most editors can, or HandBrake), open that file in Mask and export again.

## 6. Commands

In PowerShell (Windows) or Terminal (Mac and Linux), in the Mask folder (section 3 shows how to get there):

| What | Command |
|---|---|
| Open Mask in the browser | `./mask` |
| Open it with a video loaded | `./mask --video "D:\Videos\my video.mp4"` (Mac: `./mask --video ~/Movies/my-video.mov`) |
| Don't open the browser (just print the address) | `./mask --no-browser` |
| Use another port | `./mask --port 7900` |
| Check the setup | `./mask check` |
| Get the models: Balanced (and tracking), Faster, Better or all | `./mask download`, `./mask download faster`, `./mask download better`, `./mask download all` |
| Copy the models from a folder | `./mask download all --from E:\models` (Mac: `--from /Volumes/USB/models`) |
| Help | `./mask help` |

In Command Prompt or Git Bash on Windows, use `mask.bat` instead of `./mask`; on Mac and Linux, `bash mask.sh` works too.

`./mask check` shows the version, where Mask runs (graphics card, Mac GPU or processor), and which qualities have their models.

## 7. The AI models

Mask uses Meta's SAM 2.1 models (Apache License 2.0), converted to the ONNX format by Clipizo: half precision for Windows graphics cards, full precision for Macs and processors. Each quality has an image model for clicking; tracking uses one tracker. Meta's official SAM 2 code and models are at `https://github.com/facebookresearch/sam2`: point users there when they ask where the models come from.

| Quality | Windows with a graphics card | Mac, and any computer without a graphics card |
|---|---|---|
| Tracking | `sam2_track_small_fp16.onnx`, 105 MB | `sam2_track_small_coreml.onnx`, 227 MB |
| Faster | `sam2_image_tiny_fp16.onnx`, 65 MB | `sam2_image_tiny_coreml.onnx`, 157 MB |
| Balanced | `sam2_image_small_fp16.onnx`, 79 MB | `sam2_image_small_coreml.onnx`, 189 MB |
| Better | `sam2_image_large_fp16.onnx`, 437 MB | `sam2_image_large_coreml.onnx`, 910 MB |

- The installer gets Balanced and tracking. On Windows with a graphics card it also gets the processor versions of those two, in case the card can't run them.
- Another quality downloads the first time the user picks it (a progress bar shows on the picture), or with `./mask download all`.
- **Where they come from:** Clipizo's storage on Cloudflare, `https://pub-b100959e888f4b8cb607e262182f9a07.r2.dev/mask/models/v1/` (the folder also has the license, `LICENSE.txt`, and a list of the files, `README.txt`).
- **From Maskizo:** if Clipizo's Maskizo plugin for DaVinci Resolve is installed on the computer, Mask copies the models from it instead of downloading them (on Windows, Maskizo has the graphics-card files; the processor copies then come only if they're ever needed).
- Every file is checked (size and SHA-256) before it's used. An interrupted download continues where it stopped; a damaged one is set aside (as `.bad`), and the next try downloads it again.
- **Copying instead of downloading:** copy the `models` folder of another Mask install (best from the same kind of computer: a Windows PC with a graphics card uses other files than a Mac) to a USB stick, then run `./mask download all --from <that folder>`. It copies the files this computer needs and lists the ones the folder doesn't have.

## 8. Troubleshooting

**Installing:**

| What happens | What to do |
|---|---|
| *"Windows protected your PC"* when starting a `.bat` file | Click **More info** > **Run anyway**. |
| The installer window closes immediately, or Windows opens the file in Notepad | Make sure the ZIP was extracted (section 2) and double-click `install-windows.bat` itself. |
| *"It looks like you started the installer from inside the ZIP file"* | Extract the ZIP first, move the folder to `C:\Mask`, and run the installer from there. |
| *"Could not download uv"* | No internet, or the network blocks `astral.sh` or `github.com` (some school and office networks). Try another network. It isn't caused by an old Windows 10: the installer turns on the secure connection type it needs. Downloading the ZIP by clicking doesn't help here, because the installer downloads uv either way. |
| Mac or Linux: `unzip: command not found` | Use the steps in section 2: they download a `.tar.gz` and unpack it with `tar -xzf Mask.tar.gz`, which every Mac and Linux has. |
| Linux: `curl: command not found` | Download with `wget -O Mask.tar.gz https://github.com/Clipizo/Mask/archive/refs/heads/main.tar.gz` instead. |
| *"Please run the installer without sudo"* | Run `bash install.sh` without `sudo`. If an earlier run with `sudo` left files the user can't change ("Permission denied" inside the Mask folder), give the folder back once with `sudo chown -R "$USER" ~/Mask`, then run the installer again. |
| Windows: the installer says a Microsoft component is missing, or an error mentions `DLL load failed`, `WinError 126` or `onnxruntime_pybind11_state` | The installer offers to install it (Microsoft's free Visual C++ Redistributable): press Enter, then click **Yes** when Windows asks for permission. The permission prompt can open behind other windows: look for it on the taskbar. If that fails, download it from `https://aka.ms/vs/17/release/vc_redist.x64.exe`, run it, restart the computer, and run the installer again. |
| *"Installing the packages failed, 3 times"* or another download error during the install | An internet problem. Check the connection and run the installer again: it keeps what it downloaded. On school, work or some country networks, `pypi.org` or `files.pythonhosted.org` may be blocked: try another network. |
| The install looks stuck | A download can pause for a minute; wait. On Windows, if the window title starts with "Select", press Esc (clicking the window pauses it). |
| A warning about a long path, OneDrive, iCloud, Dropbox or special characters | Move the folder to `C:\Mask` (Windows) or the home folder (Mac and Linux), then run the installer again with `--repair`. |
| *"The installation doesn't load"* | Run the installer again with `--repair` (Windows: `./install-windows.bat --repair`; Mac and Linux: `bash install.sh --repair`). |
| *"Mask isn't installed yet"* | Run the installer (section 2). If it ran, look at the end of its window or `install-log.txt` for the error. |
| The folder was moved or renamed after installing | Run the installer again (it rebuilds what broke), or with `--repair`. |
| *"This Mac has an Intel processor"* | Intel Macs can't run Mask. Use a Mac with Apple Silicon, or a Windows or Linux PC. |
| Mac: "permission denied" for `./mask` | Run `bash mask.sh` instead, or run the installer again (it fixes the permission). |
| The installer ends with *"The models aren't all here yet"* | Nothing is broken: read the reason it gives. The models come the first time they're needed, or with `./mask download`. |

**Using Mask:**

| What happens | What to do |
|---|---|
| The browser doesn't open by itself | Open the address the window shows, for example `http://127.0.0.1:7861`. |
| The page says it can't connect, or stops responding | The window that runs Mask was closed: start Mask again (section 3). On Windows, if that window's title starts with "Select", press Esc in it: a click there paused Mask. |
| Mac: a message asks whether Terminal may access files in the Desktop, Documents or Downloads folder | Click **Allow**: macOS asks before a program reads those folders. If it was refused, turn it on in System Settings > **Privacy & Security** > **Files and Folders** > Terminal, or drop the video on the page instead of pasting its path. |
| *"Open a video first"* | Drop a video on the page, or paste its path and press Enter. |
| *"This file can't be opened as a video"* | The file is damaged or isn't a video. Convert it with another program (for example HandBrake) and open the copy. |
| The first click takes several seconds | Normal: the model loads on the first click, and the tracker the first time you track. After that they stay loaded until you close Mask. |
| *"... couldn't be downloaded"*, or the model download fails or is very slow | Check the internet and try again: downloads continue where they stopped. Some school, work or country networks block Cloudflare's `r2.dev` addresses: try another network, or copy the models from another computer with `./mask download all --from FOLDER` (section 7). |
| *"The GPU couldn't load ..., using the CPU"* in the window | The graphics card couldn't run that model. Update the graphics driver and restart Mask. Mask keeps working on the processor (slower). |
| Better quality says it uses Balanced | Better needs a graphics card or a Mac's GPU; on the processor Mask uses Balanced. |
| Tracking is very slow | `./mask check` shows where Mask runs. On the processor, a few seconds per frame is normal: track shorter parts (In and Out), or use a computer with a graphics card. Close other programs that use the graphics card heavily. |
| Everything is very slow or seems stuck (often an 8 GB Mac or PC) | The computer has run out of free memory. Close video editors (DaVinci Resolve, Premiere Pro), games and browsers with many tabs, or restart the computer, and try again with *Balanced* or *Faster*. On a Mac, Activity Monitor > Memory shows "Memory Pressure": red means full. |
| *"Tracking is running"* when clicking | Wait for it, or click *Stop tracking* first. |
| *"... frame(s) between In and Out have no mask yet"* when exporting | Track those frames first, or move In and Out to the frames that have masks. |
| The mask drifts onto the background | Go to the first wrong frame, click the subject there (with Cut points on the background), and track again from there. |
| An export fails | The message shows the last lines of FFmpeg's report. Check the free disk space: ProRes files are large. |
| The transparency doesn't show in DaVinci Resolve | Media Pool > right-click the clip > Clip Attributes > Alpha mode: Straight. |
| Something else goes wrong | The page shows *"Something went wrong"*, and the details are in `last-error.txt` in the Mask folder. Restart Mask (close its window and start it again). If it keeps happening, run `./mask check` and give its output, with the error text or `last-error.txt`, to your AI assistant. |

## 9. Updating, moving and uninstalling

**Updating:** keep the old folder under another name (Windows: `Rename-Item "C:\Mask" "Mask-old"`; Mac and Linux: `mv ~/Mask ~/Mask-old`), then get the new version with the steps in section 2. Before running the installer, copy the `models` folder from `Mask-old` into the new `Mask` folder, so the models don't download again. Earlier work stays in `Mask-old/output`; to continue it in the new version, copy its video folders into the new `output` folder. When the new version works, the old folder can go.

**Moving:** move the whole folder, then run the installer again in its new place (it rebuilds what the move broke).

**Uninstalling:** delete the Mask folder. Nothing else is installed on the computer, except Microsoft's Visual C++ component on Windows if the installer added it (other programs use it too, so leave it).
