# Mask: gets uv (a small tool that installs Python) and Python into the Mask folder. Started by
# install-windows.bat before app\setup_kit.py, which does the rest; it skips what is already there.
# If this script can't run (some company PCs block script files), the .bat gets uv its usual way and
# uv gets Python when setup_kit.py starts, so the install works the same.
#
# While it works, a click inside the window doesn't pause it. Windows' console window has
# "QuickEdit Mode" on by default: a click inside the window starts selecting text, and until Esc
# ends the selection (the title then starts with "Select"), every program in that window stops at
# its next line of output. This turns it off for this window only, through Windows' documented
# SetConsoleMode, and back on when it ends. It has to happen in the program that does the work:
# before each program a .bat starts, cmd.exe puts back the setting the window had when the .bat
# started. app\common.py does the same for the rest of the install and for Mask itself.
param(
    [Parameter(Mandatory = $true)][string]$UvDir,
    [Parameter(Mandatory = $true)][string]$UvVersion,
    [Parameter(Mandatory = $true)][string]$UvSha256,
    [string]$PythonVersion = "3.12"
)

$console = [IntPtr]::Zero
$savedMode = 0
try {
    Add-Type -Namespace MaskKit -Name ConsoleWindow -ErrorAction Stop -MemberDefinition @'
[DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
public static extern IntPtr CreateFileW(string name, int access, int share, IntPtr security, int creation, int flags, IntPtr template);
[DllImport("kernel32.dll", SetLastError = true)]
public static extern bool GetConsoleMode(IntPtr handle, out int mode);
[DllImport("kernel32.dll", SetLastError = true)]
public static extern bool SetConsoleMode(IntPtr handle, int mode);
'@
    # CONIN$ is the window's keyboard and mouse input (GENERIC_READ | GENERIC_WRITE, shared, OPEN_EXISTING).
    $handle = [MaskKit.ConsoleWindow]::CreateFileW('CONIN$', 0xC0000000, 3, [IntPtr]::Zero, 3, 0, [IntPtr]::Zero)
    $mode = 0
    if ($handle -ne [IntPtr](-1) -and [MaskKit.ConsoleWindow]::GetConsoleMode($handle, [ref]$mode) -and ($mode -band 0x40)) {
        # ENABLE_EXTENDED_FLAGS (0x80) without ENABLE_QUICK_EDIT_MODE (0x40) turns QuickEdit off.
        if ([MaskKit.ConsoleWindow]::SetConsoleMode($handle, ($mode -bor 0x80) -band (-bnot 0x40))) {
            $console = $handle
            $savedMode = $mode
        }
    }
} catch { }  # not allowed on this computer: the window keeps its usual behaviour

try {
    # uv: the version this kit was tested with, checked against the SHA-256 that uv publishes.
    $have = (Test-Path -LiteralPath (Join-Path $UvDir "uv.exe")) -or (Test-Path -LiteralPath (Join-Path $UvDir "bin\uv.exe"))
    if (-not $have -and $env:PROCESSOR_ARCHITECTURE -eq "AMD64") {
        Write-Host "Downloading uv (a small tool that installs Python for Mask)..."
        [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor 3072
        $ProgressPreference = "SilentlyContinue"
        $name = "uv-x86_64-pc-windows-msvc.zip"
        $zip = Join-Path (Split-Path -Parent $UvDir) "uv-$UvVersion-x86_64-pc-windows-msvc.zip"
        New-Item -ItemType Directory -Path (Split-Path -Parent $zip) -Force | Out-Null
        foreach ($url in "https://releases.astral.sh/github/uv/releases/download/$UvVersion/$name",
                         "https://github.com/astral-sh/uv/releases/download/$UvVersion/$name") {
            if ((Test-Path -LiteralPath $zip) -and (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash -eq $UvSha256) { break }
            try { Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing -TimeoutSec 120 -ErrorAction Stop } catch { }
        }
        if ((Test-Path -LiteralPath $zip) -and (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash -eq $UvSha256) {
            # Unpack next to the final folder, then move uv.exe in last: if this is interrupted, there
            # is no half-written uv.exe for the next run to trust.
            $unpacked = "$UvDir.unpacked"
            Expand-Archive -LiteralPath $zip -DestinationPath $unpacked -Force -ErrorAction Stop
            New-Item -ItemType Directory -Path $UvDir -Force | Out-Null
            foreach ($file in "uvw.exe", "uvx.exe", "uv.exe") {
                Move-Item -LiteralPath (Join-Path $unpacked $file) -Destination (Join-Path $UvDir $file) -Force -ErrorAction Stop
            }
        }
    }

    # Python, unless uv already has it here.
    $uv = Join-Path $UvDir "uv.exe"
    if (-not (Test-Path -LiteralPath $uv)) { $uv = Join-Path $UvDir "bin\uv.exe" }
    if (Test-Path -LiteralPath $uv) {
        & $uv python find $PythonVersion *> $null
        if ($LASTEXITCODE -ne 0) { & $uv python install $PythonVersion }
    }
} catch {
    Write-Host $_
} finally {
    if ($console -ne [IntPtr]::Zero) { [void][MaskKit.ConsoleWindow]::SetConsoleMode($console, $savedMode -bor 0x80) }
}
exit 0
