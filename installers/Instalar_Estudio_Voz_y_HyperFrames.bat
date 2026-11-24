@echo off
setlocal
title Estudio de Voz IA local + HyperFrames Studio (RTX 4080)
color 0A

:MENU
cls
echo ============================================================================
echo   INSTALADOR: ESTUDIO DE VOZ LOCAL + HYPERFRAMES STUDIO
echo ============================================================================
echo.
echo   1. Estudio de voz local (Voicebox, ~570 MB, modelos aparte)
echo   2. HyperFrames Studio (editar video con Claude y Gemini)
echo   3. Las dos cosas
echo   4. Salir
echo.
choice /c 1234 /n /m "Elige una opcion (1-4): "
if errorlevel 4 goto :END
if errorlevel 3 goto :BOTH
if errorlevel 2 goto :HF
if errorlevel 1 goto :VOICE

:BOTH
call :VOICE_STEPS
call :HF_STEPS
goto :FINISH

:VOICE
call :VOICE_STEPS
goto :FINISH

:HF
call :HF_STEPS
goto :FINISH

:: ----------------------------------------------------------------------------
:: Comunes
:: ----------------------------------------------------------------------------
:ENSURE_FFMPEG
ffmpeg -version >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] FFmpeg ya esta instalado.
    exit /b 0
)
winget --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [AVISO] Sin winget. Instala FFmpeg a mano: https://www.gyan.dev/ffmpeg/builds/
    exit /b 1
)
echo Instalando FFmpeg con winget...
winget install --id Gyan.FFmpeg -e --silent --accept-package-agreements --accept-source-agreements
echo [OK] FFmpeg instalado. Si no lo detecta, cierra y vuelve a abrir esta ventana.
exit /b 0

:: ----------------------------------------------------------------------------
:: Parte 1: estudio de voz local (Voicebox)
:: ----------------------------------------------------------------------------
:VOICE_STEPS
echo.
echo ===== ESTUDIO DE VOZ LOCAL =====
echo [1/3] Verificando GPU NVIDIA y CUDA...
nvidia-smi >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] No se detecto nvidia-smi. Actualiza el driver NVIDIA y repite.
    pause
    exit /b 1
)
echo [OK] GPU NVIDIA detectada.

echo [2/3] FFmpeg para audio WAV/MP3...
call :ENSURE_FFMPEG

echo [3/3] Descargando Voicebox ^(GitHub oficial jamiepine/voicebox, ultima version^)...
set "VOICE_DIR=%USERPROFILE%\EstudioVozIA"
if not exist "%VOICE_DIR%" mkdir "%VOICE_DIR%"
powershell -NoProfile -Command "$ProgressPreference='SilentlyContinue'; try { $r = Invoke-RestMethod -Uri 'https://api.github.com/repos/jamiepine/voicebox/releases/latest'; $a = $r.assets | Where-Object { $_.name -like '*x64-setup.exe' } | Select-Object -First 1; if (-not $a) { exit 1 }; Write-Host ('Descargando ' + $a.name); Invoke-WebRequest -Uri $a.browser_download_url -OutFile '%VOICE_DIR%\Voicebox_Setup.exe' } catch { Write-Host $_.Exception.Message; exit 1 }"
if exist "%VOICE_DIR%\Voicebox_Setup.exe" (
    echo [OK] Descarga completa. Abriendo el instalador de Voicebox...
    start /wait "" "%VOICE_DIR%\Voicebox_Setup.exe"
) else (
    echo [AVISO] No se pudo descargar. Abriendo la pagina de releases...
    start https://github.com/jamiepine/voicebox/releases/latest
)
echo.
echo Ajustes recomendados en Voicebox para la RTX 4080 de 16 GB:
echo   1. Settings, GPU: NVIDIA CUDA ^(descarga las librerias CUDA que pide, ~2 GB^).
echo   2. Modelos: Qwen3-TTS 1.7B y Chatterbox Multilingual.
echo   3. Muestras de voz: WAV 48 kHz, 24 bit, mono, sin ruido.
echo   4. Clona solo tu propia voz o voces con permiso.
exit /b 0

:: ----------------------------------------------------------------------------
:: Parte 2: HyperFrames Studio + habilidades para Claude y Gemini
:: ----------------------------------------------------------------------------
:HF_STEPS
echo.
echo ===== HYPERFRAMES STUDIO =====
echo [1/5] Verificando Node.js 22 o superior...
node -e "process.exit(parseInt(process.versions.node)>=22?0:1)" >nul 2>&1
if %errorlevel% neq 0 (
    winget --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] Falta Node.js 22+ y no hay winget. Instala desde https://nodejs.org y repite.
        pause
        exit /b 1
    )
    echo Instalando Node.js LTS con winget...
    winget install --id OpenJS.NodeJS.LTS -e --silent --accept-package-agreements --accept-source-agreements
    echo [AVISO] Node.js instalado. CIERRA esta ventana y vuelve a ejecutar el instalador para que lo detecte.
    pause
    exit /b 1
)
echo [OK] Node.js listo.

echo [2/5] FFmpeg para renderizar el MP4...
call :ENSURE_FFMPEG

echo [3/5] Descargando HyperFrames Studio ^(app de escritorio, cuenta gratuita de HeyGen^)...
set "HF_DIR=%USERPROFILE%\HyperFramesStudio"
if not exist "%HF_DIR%" mkdir "%HF_DIR%"
powershell -NoProfile -Command "$ProgressPreference='SilentlyContinue'; try { Invoke-WebRequest -Uri 'https://hyperframes.studio/studio/download?os=windows&src=docs-install' -OutFile '%HF_DIR%\HyperFrames-win-x64.zip'; Expand-Archive -Path '%HF_DIR%\HyperFrames-win-x64.zip' -DestinationPath '%HF_DIR%' -Force } catch { Write-Host $_.Exception.Message; exit 1 }"
if %errorlevel% neq 0 (
    echo [AVISO] Fallo la descarga. Abre la pagina oficial y descarga el zip de Windows.
    start https://hyperframes.heygen.com/
) else (
    set "HF_EXE="
    for /f "delims=" %%f in ('dir /b /s "%HF_DIR%\HyperFrames.exe" 2^>nul') do set "HF_EXE=%%f"
    if defined HF_EXE (
        powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\HyperFrames Studio.lnk'); $s.TargetPath='%HF_EXE%'; $s.Save()"
        echo [OK] HyperFrames Studio en %HF_DIR% con acceso directo en el escritorio.
    ) else (
        echo [AVISO] No encontre HyperFrames.exe dentro de %HF_DIR%.
    )
)

echo [4/5] Habilidades de HyperFrames para Claude Code...
where claude >nul 2>&1
if %errorlevel% equ 0 (
    call claude plugin marketplace add heygen-com/hyperframes
    call claude plugin install hyperframes@hyperframes
) else (
    echo [AVISO] Claude Code no esta en el PATH; salto el plugin.
)

echo [5/5] Habilidades de HyperFrames para Gemini...
echo Se abrira el selector de HyperFrames: elige Core Skills y marca tu agente Gemini
echo ^(si no aparece Gemini CLI, elige Google Antigravity^).
pause
call npx --yes skills add heygen-com/hyperframes
echo.
echo Para editar: abre HyperFrames Studio, inicia sesion con HeyGen y elige Claude Code
echo como agente en la primera pantalla. En el terminal: claude, luego /hyperframes:hyperframes
exit /b 0

:FINISH
echo.
echo ============================================================================
echo   LISTO. Reinicia Claude Code o usa /reload-plugins para ver las skills.
echo ============================================================================
pause
:END
endlocal
