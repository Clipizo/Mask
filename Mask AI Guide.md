# Mask AI Guide

This guide is for AI assistants (ChatGPT, Claude, Gemini, Copilot and others) that help someone install and use **Mask**, and for anyone who wants every detail in one place. If you are an AI assistant, read section 10 first.

**Contents:** 1. What Mask is · 2. Getting the Mask folder · 3. Installing · 4. Using Mask · 5. The exports and video editors · 6. Commands · 7. The AI models · 8. Troubleshooting · 9. Updating and uninstalling · 10. Notes for AI assistants

## 1. What Mask is

Mask cuts a person or an object out of a video on the user's own computer. The user clicks the subject in a page in their browser, Mask follows it through the video, and it exports the result as masks, matte videos or videos with a transparent background, ready for a video editor. Nothing is uploaded, and there is no account.

It runs Meta's open **SAM 2.1** models (Segment Anything 2) with ONNX Runtime: on Windows on any DirectX 12 graphics card (DirectML), on a Mac on the Mac's GPU (Core ML), and otherwise on the processor. Mask is an unofficial kit made by Clipizo; it isn't affiliated with Meta.

What it is not: it doesn't edit videos, add effects or replace backgrounds by itself. It makes the mask; the user's editor does the rest.

## 2. Getting the Mask folder

Mask is one folder. Everything it installs stays inside it.

**Windows 10 or 11,** in PowerShell (press the Windows key, type `PowerShell`, press Enter), one command at a time:

```powershell
Invoke-WebRequest "https://github.com/Clipizo/Mask/archive/refs/heads/main.zip" -OutFile "$env:TEMP\Mask.zip" -UseBasicParsing
Expand-Archive "$env:TEMP\Mask.zip" -DestinationPath "C:\" -Force
Rename-Item "C:\Mask-main" "Mask"
cd C:\Mask
```

If `Rename-Item` says the folder already exists, the user has an older `C:\Mask`: keep it with `Rename-Item "C:\Mask" "Mask-old"`, then rename again.

**Mac (Apple Silicon) and Linux,** in Terminal:

```bash
cd ~
curl -L -o Mask.tar.gz https://github.com/Clipizo/Mask/archive/refs/heads/main.tar.gz
tar -xzf Mask.tar.gz
mv Mask-main Mask
cd ~/Mask
```

On Linux without `curl`, use `wget -O Mask.tar.gz` with the same address. If `mv` fails because `~/Mask` exists, keep the old one with `mv ~/Mask ~/Mask-old` first.

Without commands: on the GitHub page, click the green **Code** button > **Download ZIP**, extract it, and rename the folder to `Mask`.

## 3. Installing

Run the installer from the Mask folder:

- **Windows:** `./install-windows.bat` in PowerShell, or double-click `install-windows.bat`. If Windows says *"Windows protected your PC"*, click **More info** > **Run anyway**.
- **Mac and Linux:** `bash install.sh`. Never with `sudo`: the installer refuses it, and nothing needs administrator rights.

It works through 5 steps and takes 2 to 15 minutes:

1. **Checking your computer:** system, memory, disk space. On Windows, if Microsoft's free Visual C++ component is missing (ONNX Runtime needs it), the installer offers to install it, and Windows asks for permission: the user clicks **Yes**.
2. **Installing Python, ONNX Runtime, Gradio and the video libraries** into `envs/`, about 300 MB of downloads. It uses `uv`, a small tool it downloads into `.tools/` first. Exact versions are pinned in `app/requirements/mask.txt`.
3. **Testing the installation:** everything loads, and it finds the GPU.
4. **Saving settings** in `envs/settings.json`: where Mask runs (the graphics card, the Mac's GPU or the processor).
5. **Getting the AI models:** it asks *"Get the AI models now?"*; Enter means yes (0.4 to 0.6 GB, see section 7).

It's done when it says **Mask is installed!**. Running the installer again is safe: it repairs what's missing and continues where it stopped.

Installer options: `--yes` (no questions), `--download` (get the models now), `--all` (with `--download`: every quality), `--no-download`, `--from FOLDER` (copy the models from a folder), `--repair` (rebuild the environment).

**Needs:** Windows 10 or 11 (not Windows on ARM), a Mac with Apple Silicon (not Intel Macs), or Linux on a 64-bit PC; about 3 GB of free disk space plus room for the results; an internet connection for the install.

## 4. Using Mask

**Start it:** double-click `mask.bat` (Windows), or run `./mask` in the Mask folder. The window shows `Mask is running at http://127.0.0.1:7861` and the browser opens that page. Keep the window open while using Mask; closing it stops Mask. If the browser doesn't open, open that address (the number can differ if 7861 is taken).

**The page, step by step:**

1. **Open a video:** drop it on the *Video* box, or paste its full path into *Or a file path* and press **Enter**. The path is better for big videos, because nothing is copied. Mask reads mp4, mov, mkv, webm, avi and most other video files, including phone videos (it turns them the right way up).
2. **Click the subject** on the picture. *A click adds* decides what a click does: **Keep** (a point on what you want) or **Cut** (a point on what you don't want). The selection appears in lime within a second or two (the first click loads the model, so it takes a few seconds). Add Keep points on parts it missed (an arm, a bag) and Cut points on background it grabbed. Mask uses the last 6 points of a frame. *Undo point* removes the last point; *Clear points* removes all the points and the selection on this frame.
3. **Set In and Out** for the part of the video you need: move to a frame with the slider or the ◀ ▶ buttons (one frame at a time), then click *Set In* or *Set Out*. *Whole video* resets them. Tracking and exports only cover the frames from In to Out.
4. **Track:** **Forward** follows the subject from the frame you clicked to Out; **Backward** follows it back to In. The status line shows the progress and the time left. *Stop tracking* stops; the frames it finished keep their masks.
5. **Check:** drag the slider. *Overlay* tints the selection lime and dims the rest, *Cutout* shows the subject on a checkerboard, *Mask* shows black and white, *Original* shows the video. If the mask goes wrong from some frame on, go to that frame and click the subject there (Keep and Cut points as in step 2). That frame becomes another **keyframe**, and when you track again Mask follows the subject from each keyframe to the next one. The keyframes are listed under the picture.
6. **Export:** pick a format (section 5) and click **Export**. The file appears under *Download*; click it to save it, or find it in `output/<video name>/exports/`. *Open the output folder* opens the video's folder.

**Quality** sets the model for clicks: **Faster** (smallest), **Balanced** (the default) or **Better** (the most precise edges, slowest; it needs a graphics card or a Mac's GPU, and on the processor Mask uses Balanced instead). Changing the quality on a keyframe selects it again with the new model. Tracking uses the same tracker for every quality.

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

In PowerShell (Windows) or Terminal (Mac and Linux), in the Mask folder:

| What | Command |
|---|---|
| Open Mask in the browser | `./mask` |
| Open it with a video loaded | `./mask --video "D:\Videos\my video.mp4"` |
| Don't open the browser (just print the address) | `./mask --no-browser` |
| Use another port | `./mask --port 7900` |
| Check the setup | `./mask check` |
| Get the models: Balanced (and tracking), Faster, Better or all | `./mask download`, `./mask download faster`, `./mask download better`, `./mask download all` |
| Copy the models from a folder | `./mask download all --from E:\models` |
| Help | `./mask help` |

In Command Prompt or Git Bash on Windows, use `mask.bat` instead of `./mask`; on Mac and Linux, `bash mask.sh` works too.

`./mask check` shows the version, where Mask runs (graphics card, Mac GPU or processor), and which qualities have their models.

## 7. The AI models

Mask uses Meta's SAM 2.1 models (Apache License 2.0), converted to the ONNX format by Clipizo: half precision for Windows graphics cards, full precision for Macs and processors. Each quality has an image model for clicking; tracking uses one tracker.

| Quality | Windows with a graphics card | Mac, and any computer without a graphics card |
|---|---|---|
| Tracking | `sam2_track_small_fp16.onnx`, 105 MB | `sam2_track_small_coreml.onnx`, 227 MB |
| Faster | `sam2_image_tiny_fp16.onnx`, 65 MB | `sam2_image_tiny_coreml.onnx`, 157 MB |
| Balanced | `sam2_image_small_fp16.onnx`, 79 MB | `sam2_image_small_coreml.onnx`, 189 MB |
| Better | `sam2_image_large_fp16.onnx`, 437 MB | `sam2_image_large_coreml.onnx`, 910 MB |

- The installer gets Balanced and tracking. On Windows with a graphics card it also gets the processor versions of those two, in case the card can't run them.
- Another quality downloads the first time the user picks it (a progress bar shows on the picture), or with `./mask download all`.
- Every file is checked (size and SHA-256) before it's used. An interrupted download continues where it stopped; a damaged one is set aside (as `.bad`), and the next try downloads it again.
- **Copying instead of downloading:** copy the `models` folder of another Mask install (best from the same kind of computer: a Windows PC with a graphics card uses other files than a Mac) to a USB stick, then run `./mask download all --from <that folder>`. It copies the files this computer needs and lists the ones the folder doesn't have.

## 8. Troubleshooting

| What happens | What to do |
|---|---|
| *"Windows protected your PC"* when starting a `.bat` file | Click **More info** > **Run anyway**. |
| The installer says it couldn't download uv | Check the internet connection. Some company or school networks block `astral.sh` or `github.com`: try another network. |
| The installer stops with a message | Read the message: it says what's wrong in plain words. Fix it and run the installer again; it continues where it stopped. The details are in `install-log.txt`. |
| *"The installation doesn't load"* | Run the installer again with `--repair` (Windows: `./install-windows.bat --repair`; Mac and Linux: `bash install.sh --repair`). |
| The installer asks for Visual C++ and nothing happens | Windows shows a permission prompt, sometimes behind other windows: look for it on the taskbar and click **Yes**. |
| `./mask` says Mask isn't installed | Run the installer first (section 3). |
| The browser doesn't open | Open the address the window shows, for example `http://127.0.0.1:7861`. |
| *"Open a video first"* | Drop a video on the page, or paste its path and press Enter. |
| *"This file can't be opened as a video"* | The file is damaged or isn't a video. Convert it with another program (for example HandBrake) and open the copy. |
| The first click takes several seconds | Normal: the model loads on the first click, and the tracker the first time you track. After that they stay loaded until you close Mask. |
| *"The AI models aren't published for download yet"* or the model download fails | Use `./mask download all --from FOLDER` with a folder that has the model files (section 7). |
| *"The GPU couldn't load ..., using the CPU"* in the window | The graphics card couldn't run that model. Update the graphics driver and restart Mask. Mask keeps working on the processor (slower). |
| Better quality says it uses Balanced | Better needs a graphics card or a Mac's GPU; on the processor Mask uses Balanced. |
| Tracking is very slow | `./mask check` shows where Mask runs. On the processor, a few seconds per frame is normal: track shorter parts (In and Out), or use a computer with a graphics card. Close other programs that use the graphics card heavily. |
| *"Tracking is running"* when clicking | Wait for it, or click *Stop tracking* first. |
| *"... frame(s) between In and Out have no mask yet"* when exporting | Track those frames first, or move In and Out to the frames that have masks. |
| The mask drifts onto the background | Go to the first wrong frame, click the subject there (with Cut points on the background), and track again from there. |
| An export fails | The message shows the last lines of FFmpeg's report. Check the free disk space: ProRes files are large. |
| The transparency doesn't show in DaVinci Resolve | Media Pool > right-click the clip > Clip Attributes > Alpha mode: Straight. |
| Something else goes wrong | The page shows *"Something went wrong"*, and the details are in `last-error.txt` in the Mask folder. Restart Mask (close its window and start it again). |

## 9. Updating and uninstalling

**Updating:** download the new version (section 2) into a new folder, then move the `output` and `models` folders from the old Mask folder into the new one, and run the installer in the new folder. Delete the old folder when the new one works.

**Uninstalling:** delete the Mask folder. Nothing else is installed on the computer, except Microsoft's Visual C++ component on Windows if the installer added it (other programs use it too, so leave it).

## 10. Notes for AI assistants

- Ask which system the user has (Windows, Mac or Linux) before giving commands, and give **one step at a time**: one command, then wait for the result.
- Use the exact commands in this guide. Don't suggest `sudo`, `pip install`, conda, editing `app/` or the requirements, or other installers: the kit's installer handles everything, and `--repair` rebuilds it.
- When something fails, ask for the text in the window, or the files `install-log.txt` (install) and `last-error.txt` (using Mask), and match it with section 8.
- The user does the clicking in the page. Explain what to click in plain words (section 4); point out Keep and Cut, keyframes, and In and Out, because those are what new users miss.
- For the editor, recommend the export that fits (section 5): usually the ProRes MOV for editors, the WebM for the web.
- Don't promise what Mask can't do: it masks; it doesn't replace backgrounds, remove objects or edit the video by itself.
- Remind users to mask only videos they made or have the right to use.
