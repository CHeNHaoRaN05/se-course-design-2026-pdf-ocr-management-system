@echo off
chcp 936 >nul
setlocal EnableDelayedExpansion
title PDF-System Dev Launcher
cd /d "%~dp0"

rem ============================================================
rem  PDF 文件显示与管理系统 —— 本地运行环境一键启动器（cmd / 双击可用）
rem  用法：
rem      start_dev.bat              交互式菜单（默认一键启动）
rem      start_dev.bat backend      仅启动后端   http://127.0.0.1:8000/docs
rem      start_dev.bat frontend     仅启动前端   http://127.0.0.1:5173
rem      start_dev.bat setup        仅安装/修复环境（建 venv、装依赖、生成 .env、建表）
rem      start_dev.bat test         跑后端 pytest
rem      start_dev.bat reset-db     删库重建（MySQL 用户请手动 DROP 后跑 setup）
rem      start_dev.bat stop         关掉占用 8000/5173 端口的本地服务
rem      start_dev.bat --reload backend   带热重载启动后端
rem ============================================================

rem ---------------------- 可配置项 ----------------------
set "SYS=%CD%\pdf_system"
set "FE=%SYS%\frontend"
set "VENV=%SYS%\.venv"
set "PY=%VENV%\Scripts\python.exe"
set "PORT_BE=8000"
set "PORT_FE=5173"
set "RELOAD=0"
rem pip 镜像源：国内提速；若公司网络拦截镜像，改成 set "PIP_INDEX="
set "PIP_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple"
rem 是否顺带装 opencv-python-headless（OCR 模块挂载需要，失败不影响主系统）
set "WITH_OCR_DEPS=1"

rem ---------------------- 参数解析 ----------------------
if /i "%~1"=="--reload" ( set "RELOAD=1" & shift )
if /i "%~1"=="help"     goto :usage
if /i "%~1"=="/?"       goto :usage
if /i "%~1"=="setup"    goto :only_setup
if /i "%~1"=="backend"  goto :only_backend
if /i "%~1"=="frontend" goto :only_frontend
if /i "%~1"=="test"     goto :only_test
if /i "%~1"=="stop"     goto :do_stop
if /i "%~1"=="reset-db" goto :do_reset_db
if not "%~1"=="" ( echo [X] 未知参数: %~1 & goto :usage )
goto :menu

rem ---------------------- 菜单 ----------------------
:menu
echo.
echo ============================================================
echo   PDF 文件显示与管理系统 —— 本地环境启动器
echo   项目目录: %SYS%
echo ============================================================
echo   [1] 一键启动（后端 + 前端）      默认
echo   [2] 仅启动后端       127.0.0.1:%PORT_BE%/docs
echo   [3] 仅启动前端       127.0.0.1:%PORT_FE%
echo   [4] 仅安装 / 修复环境（不启动）
echo   [5] 运行后端测试（pytest）
echo   [6] 重置开发数据库
echo   [7] 停止已启动的服务
echo   [0] 退出
echo ------------------------------------------------------------
set "CH=1"
set /p "CH=请选择并回车 [1]: "
if "%CH%"=="1" goto :run_all
if "%CH%"=="2" goto :only_backend
if "%CH%"=="3" goto :only_frontend
if "%CH%"=="4" goto :only_setup
if "%CH%"=="5" goto :only_test
if "%CH%"=="6" goto :do_reset_db
if "%CH%"=="7" goto :do_stop
if "%CH%"=="0" goto :end
echo [X] 无效选择: %CH%
goto :menu

:run_all
call :setup
if errorlevel 1 goto :end
call :start_backend
call :start_frontend
call :open_browser
goto :end

:only_setup
call :setup
goto :end

:only_backend
call :setup
if errorlevel 1 goto :end
call :start_backend
call :open_browser
goto :end

:only_frontend
call :start_frontend
goto :end

:only_test
call :setup
if errorlevel 1 goto :end
pushd "%SYS%"
"%PY%" -m pytest backend/tests -q
set "RC=!errorlevel!"
popd
exit /b !RC!

rem ============================================================
rem  环境准备：Python -> venv -> 依赖 -> .env -> 建表
rem ============================================================
:setup
echo.
echo ===== 环境检查 =====
if not exist "%SYS%\backend\main.py" (
    echo [X] 未找到 %SYS%\backend\main.py
    echo     请把 start_dev.bat 放在仓库根目录（与 pdf_system 同级）
    exit /b 1
)

echo [1/4] 检查 Python ...
call :find_python
if errorlevel 1 exit /b 1

if not exist "%PY%" (
    echo     创建虚拟环境: %VENV%
    %PYEXE% -m venv "%VENV%"
    if errorlevel 1 ( echo [X] 虚拟环境创建失败 & exit /b 1 )
) else (
    echo     虚拟环境已存在: %VENV%
)
if not exist "%PY%" ( echo [X] 未找到 %PY% & exit /b 1 )

call :install_deps
if errorlevel 1 exit /b 1

call :ensure_env
call :init_db
exit /b 0

rem ---------------------- 找 Python ----------------------
:find_python
set "PYEXE="
where py >nul 2>nul
if not errorlevel 1 (
    py -3.12 -c "import sys" >nul 2>nul
    if not errorlevel 1 set "PYEXE=py -3.12"
)
if not defined PYEXE (
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3 -c "import sys" >nul 2>nul
        if not errorlevel 1 set "PYEXE=py -3"
    )
)
if not defined PYEXE (
    python -c "import sys" >nul 2>nul
    if not errorlevel 1 set "PYEXE=python"
)
if not defined PYEXE (
    echo [X] 未找到 Python，请先安装 Python 3.12 并保证 py / python 在 PATH 中
    exit /b 1
)
echo     使用: %PYEXE%
exit /b 0

rem ---------------------- 装依赖 ----------------------
:install_deps
"%PY%" -c "import fastapi,uvicorn,sqlalchemy,pydantic_settings,jwt,pypdfium2,PIL,pytest,httpx" >nul 2>nul
if not errorlevel 1 (
    echo [2/4] 依赖已就绪，跳过安装
    goto :ocr_deps
)
echo [2/4] 安装后端依赖（首次较慢，请耐心等待）...
set "PYMIN=0"
set "PYMAJ=0"
for /f "delims=" %%v in ('"%PY%" -c "import sys; print(sys.version.split()[0])"') do set "PYVER=%%v"
for /f "tokens=1,2 delims=." %%a in ("%PYVER%") do ( set "PYMAJ=%%a" & set "PYMIN=%%b" )
set "NEWPY=0"
if "%PYMAJ%"=="3" if %PYMIN% GEQ 14 set "NEWPY=1"
if "%PYMAJ%" GTR 3 set "NEWPY=1"
set "IDXOPT="
if defined PIP_INDEX set "IDXOPT=-i %PIP_INDEX%"
"%PY%" -m pip install --disable-pip-version-check %IDXOPT% pip >nul 2>nul
if "%NEWPY%"=="1" (
    echo     检测到 Python %PYVER%，改用 3.14+ 兼容版本组
    "%PY%" -m pip install --disable-pip-version-check %IDXOPT% fastapi==0.159.1 uvicorn==0.54.0 SQLAlchemy==2.1.6 pydantic==2.14.1 pydantic-settings==2.16.1 PyJWT==2.15.1 python-multipart==0.0.32 pypdfium2==5.14.0 Pillow==13.0.0 pytest==9.1.1 httpx==0.28.1
) else (
    "%PY%" -m pip install --disable-pip-version-check %IDXOPT% -r "%SYS%\requirements.txt"
)
if errorlevel 1 (
    echo [X] 依赖安装失败。可尝试把脚本里的 PIP_INDEX 清空后重试
    exit /b 1
)

:ocr_deps
if not "%WITH_OCR_DEPS%"=="1" exit /b 0
"%PY%" -c "import cv2" >nul 2>nul
if not errorlevel 1 exit /b 0
echo     可选依赖：opencv-python-headless（OCR 模块挂载需要）
"%PY%" -m pip install --disable-pip-version-check %IDXOPT% opencv-python-headless
if errorlevel 1 echo [!] 可选依赖安装失败，OCR 将降级为未挂载，其余功能不受影响
exit /b 0

rem ---------------------- 生成 .env ----------------------
:ensure_env
if exist "%SYS%\.env" (
    echo [3/4] .env 已存在，保留原配置
    exit /b 0
)
echo [3/4] 生成 .env（默认 SQLite 开发库，无需 MySQL）...
set "SECRET="
for /f "usebackq delims=" %%s in (`powershell -NoProfile -Command "$b=New-Object byte[] 36; [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b); ([Convert]::ToBase64String($b)).Replace('+','').Replace('/','').Replace('=','')"`) do set "SECRET=%%s"
if not defined SECRET set "SECRET=%RANDOM%%RANDOM%%RANDOM%%RANDOM%%RANDOM%%RANDOM%%RANDOM%%RANDOM%0123456789abcdef"
(
    echo # generated by start_dev.bat - safe to edit
    echo # default: SQLite dev database, no MySQL needed
    echo # PDF_DATABASE_URL=mysql+pymysql://pdf_user:pdf_pwd@127.0.0.1/pdf_system?charset=utf8mb4
    echo PDF_JWT_SECRET=!SECRET!
    echo PDF_JWT_ISSUER=pdf-system
    echo PDF_JWT_AUDIENCE=ocr-api
    echo PDF_JWT_EXPIRE_MINUTES=120
    echo PDF_STORAGE_DIR=./data/storage
    echo PDF_MAX_UPLOAD_BYTES=20971520
    echo PDF_MAX_PAGES=100
    echo PDF_MONTHLY_PAGE_QUOTA=500
    echo PDF_OCR_ENABLED=true
    echo PDF_OCR_DEVICE=cpu
) > "%SYS%\.env"
echo     已写入 %SYS%\.env
exit /b 0

rem ---------------------- 建表 ----------------------
:init_db
echo [4/4] 初始化数据库 ...
if not exist "%SYS%\data" mkdir "%SYS%\data"
pushd "%SYS%"
"%PY%" -m backend.scripts.init_db
set "RC=!errorlevel!"
popd
if not "%RC%"=="0" (
    echo [!] 建表失败（后端仍会启动，但接口会报错）
    echo     若使用 MySQL：先起 MySQL 服务，再把 .env 里的 PDF_DATABASE_URL 改对
    exit /b 0
)
exit /b 0

rem ============================================================
rem  启动服务
rem ============================================================
:start_backend
call :port_busy %PORT_BE%
if "%BUSY%"=="1" (
    echo [!] 端口 %PORT_BE% 已被占用，跳过启动后端（若已在运行可忽略）
    exit /b 0
)
set "RL="
if "%RELOAD%"=="1" set "RL=--reload"
echo.
echo ===== 启动后端：http://127.0.0.1:%PORT_BE%/docs =====
start "PDF-Backend" /d "%SYS%" cmd /k ""%PY%" -m uvicorn backend.main:create_app --factory --host 127.0.0.1 --port %PORT_BE% %RL%"
exit /b 0

:start_frontend
where npm >nul 2>nul
if errorlevel 1 (
    echo [!] 未检测到 npm / Node.js，跳过前端（后端仍可独立访问）
    exit /b 0
)
if not exist "%FE%\node_modules" (
    echo.
    echo ===== 安装前端依赖（首次较慢）=====
    pushd "%FE%"
    call npm install
    set "RC=!errorlevel!"
    popd
    if not "!RC!"=="0" ( echo [X] npm install 失败 & exit /b 1 )
)
echo.
echo ===== 启动前端：http://127.0.0.1:%PORT_FE% =====
start "PDF-Frontend" /d "%FE%" cmd /k "npm run dev"
exit /b 0

rem ---------------------- 端口占用检查 ----------------------
:port_busy
set "BUSY=0"
netstat -ano | findstr ":%~1 " | findstr "LISTENING" >nul 2>nul
if not errorlevel 1 set "BUSY=1"
exit /b 0

rem ---------------------- 等待就绪并开浏览器 ----------------------
:open_browser
set "OK=0"
where curl >nul 2>nul
if errorlevel 1 ( timeout /t 6 /nobreak >nul & goto :do_open )
echo 等待后端就绪 ...
for /l %%i in (1,1,30) do (
    curl -s -f http://127.0.0.1:%PORT_BE%/health >nul 2>nul
    if not errorlevel 1 ( set "OK=1" & goto :do_open )
    timeout /t 1 /nobreak >nul
)
:do_open
if "%OK%"=="1" ( echo 后端已就绪 ) else ( echo [!] 后端 30 秒内未就绪，请看 PDF-Backend 窗口的报错 )
start "" http://127.0.0.1:%PORT_BE%/docs
start "" http://127.0.0.1:%PORT_FE%/
exit /b 0

rem ---------------------- 停止服务 ----------------------
:do_stop
echo 停止占用 %PORT_BE% / %PORT_FE% 的本地服务 ...
for %%P in (%PORT_BE% %PORT_FE%) do (
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%%P " ^| findstr LISTENING') do (
        echo   kill PID %%a ^(port %%P^)
        taskkill /f /pid %%a >nul 2>nul
    )
)
exit /b 0

rem ---------------------- 重置开发库 ----------------------
:do_reset_db
echo 重置开发数据库 ...
if exist "%SYS%\data\dev.sqlite3" (
    del /f /q "%SYS%\data\dev.sqlite3"
    echo     已删除 data\dev.sqlite3
) else (
    echo     未找到 data\dev.sqlite3（可能用的是 MySQL，请手动 DROP DATABASE 后再跑 setup）
)
call :setup
goto :end

rem ---------------------- 帮助 ----------------------
:usage
echo.
echo 用法: start_dev.bat [setup ^| backend ^| frontend ^| test ^| reset-db ^| stop ^| --reload backend ^| help]
echo.
echo   无参数运行 = 交互式菜单
echo   setup      建 venv / 装依赖 / 生成 .env / 建表，不启动
echo   backend    后端  http://127.0.0.1:%PORT_BE%/docs
echo   frontend   前端  http://127.0.0.1:%PORT_FE%
echo   test       后端 pytest
echo   reset-db   删 SQLite 开发库后重建
echo   stop       结束占用 %PORT_BE%/%PORT_FE% 的进程
echo.
goto :end

:end
echo.
echo 完成。常用参数：setup / backend / frontend / test / stop / reset-db / --reload
pause
exit /b 0
