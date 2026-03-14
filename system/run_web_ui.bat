@echo off
cd /d "%~dp0"
echo.
echo(                                                                                                     
echo(                                                                     ##                             
echo(                                                                    %%#####                          
echo(                                                             #####  %%########                       
echo(                                                          ########  %%###########%%                   
echo(                                                       ###########  %%##############                 
echo(                                                   %%##############  %%##################             
echo(                                                ##################  %%#####################          
echo(                                             #####################  %%########################       
echo(                                          ########################  %%###########################    
echo(                                       ###########################  %%###########################    
echo(                                       ###########################  %%########################       
echo(                                 ####    #########################  %%#####################          
echo(                                 ######%%     #####################  %%#################%%             
echo(                          #####  ##########    %%##################  %%###############                
echo(                      %%########  #############     ###############  %%###########%%                   
echo(                    ###########  ################     ############  %%########                       
echo(                ###############  ###################     #########  %%#####                          
echo(             ##################  ######################%%    %%#####   ##                             
echo(          #####################  #########################     ###                                  
echo(       ########################  ###########################                                        
echo(    ###########################  ##########################     ##                                  
echo(   ############################  #######################     ######                                 
echo(     ##########################  ####################     #########                                 
echo(        %%######################  #################     ############                                 
echo(           ####################  ##############     ###############                                 
echo(              #################  ###########    ###################                                 
echo(                  #############  #######     ######################                                 
echo(                     ##########  #####    #########################                                 
echo(                        #######        %%###########################                                 
echo(                           %%##%%        ############################                                 
echo(                                 ######   #########################                                 
echo(                                 ########%%   ######################                                 
echo(                                 ############   ###################                                 
echo(                                 ###############    ###############                                 
echo(                                 ##################    ############                                 
echo(                                 #####################    #########                                 
echo(                                 ########################%%   ######                                 
echo(                                 ###########################     #                                  
echo(                                 ############################   %%#                                  
echo(                                 ##########################  ######                                 
echo(                                 ######################%%  %%########                                 
echo(                                 ###################%%  ############                                 
echo(                                 ################   ###############                                 
echo(                                 #############   ##################                                 
echo(                                 ##########  ######################                                 
echo(                                 ######%%   ########################                                 
echo(                                  ###  ############################                                 
echo(                                       ############################                                 
echo(                                 ####%%    #########################                                 
echo(                                 ########   #######################                                 
echo(                                 ###########    ###################                                 
echo(                                 ##############    ################                                 
echo(                                 #################%%   #############                                 
echo(                                 ####################%%   ##########                                 
echo(                                 ########################   #######                                 
echo(                                 ###########################   ###    #                             
echo(                                 ############################        #####                          
echo(                                 ##########################%%   ####  #########                      
echo(                                 #######################   %%#######  ############                   
echo(                                 ####################    ##########  ###############                
echo(                                 #################   %%#############  ##################             
echo(                                 ##############   #################  #####################%%         
echo(                                 ##########%%   ####################  ########################       
echo(                                 ########   #######################  ############################   
echo(                                 %%###    ##########################  ############################   
echo(                                       ############################  #########################%%     
echo(                                  ###   %%##########################  ######################         
echo(                                  ######    #######################  ###################            
echo(                            ###   #########   %%####################  ################               
echo(                        #######   ############    #################  #############                  
echo(                      #########   ###############    %%#############  #########                      
echo(                  #############   ##################%%   ###########  #######                        
echo(               ################   ######################   ########  ###%%                           
echo(            ###################   #########################   #####                                 
echo(         ######################   ###########################                                       
echo(      #########################   ###########################                                       
echo(    ###########################   ########################                                          
echo(     ##########################   #####################                                             
echo(        #######################   #################                                                 
echo(           ####################   ##############                                                    
echo(              #################   ###########                                                       
echo(                  #############   #######%%                                                          
echo(                    %%##########   #####                                                             
echo(                        #######                                                                     
echo(                           ####                                                                     
echo(                                                                                                    
echo(                                                                                                    
echo.
echo =================================================
echo UNLZ AI STUDIO - WEB UI
echo =================================================
echo.
where npm >nul 2>&1
if errorlevel 1 (
    echo ERROR: npm not found. Install Node.js LTS and try again.
    echo https://nodejs.org/
    pause
    exit /b 1
)

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "ROOT_DIR=%%~fI"
set "WEB_UI_DIR=%SCRIPT_DIR%web_ui"
set "LOG_DIR=%SCRIPT_DIR%logs"
set "BRIDGE_SCRIPT=%SCRIPT_DIR%web_bridge.py"
set "BRIDGE_PORT=8787"
set "PYTHON_EXE=python"

if exist "%ROOT_DIR%\venv\Scripts\python.exe" (
    set "PYTHON_EXE=%ROOT_DIR%\venv\Scripts\python.exe"
)

"%PYTHON_EXE%" -V >nul 2>&1
if errorlevel 1 (
    echo ERROR: python not found or not executable: "%PYTHON_EXE%"
    echo Install Python and/or create venv in repo root.
    pause
    exit /b 1
)

if /i "%UNLZ_DRY_RUN%"=="1" (
    echo [DRY-RUN] PYTHON_EXE="%PYTHON_EXE%"
    echo [DRY-RUN] BRIDGE_SCRIPT="%BRIDGE_SCRIPT%"
    echo [DRY-RUN] WEB_UI_DIR="%WEB_UI_DIR%"
    exit /b 0
)

cd /d "%WEB_UI_DIR%"
if not exist "node_modules" (
    echo Installing dependencies...
    npm install
)
echo.
echo Starting Web Bridge on http://127.0.0.1:%BRIDGE_PORT%
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "BRIDGE_OUT=%LOG_DIR%\web_bridge.out.log"
set "BRIDGE_ERR=%LOG_DIR%\web_bridge.err.log"

for /f "tokens=5" %%P in ('netstat -ano ^| findstr /r /c:":%BRIDGE_PORT% .*LISTENING"') do (
  taskkill /PID %%P /F >nul 2>&1
)

powershell -NoProfile -Command ^
  "Start-Process -FilePath '%PYTHON_EXE%' -ArgumentList '%BRIDGE_SCRIPT%' -WorkingDirectory '%SCRIPT_DIR%' -WindowStyle Hidden -RedirectStandardOutput '%BRIDGE_OUT%' -RedirectStandardError '%BRIDGE_ERR%'"

for /l %%i in (1,1,60) do (
  powershell -NoProfile -Command "$client = New-Object Net.Sockets.TcpClient; try { $client.Connect('127.0.0.1', %BRIDGE_PORT%); $client.Close(); exit 0 } catch { exit 1 }" >nul 2>&1
  if not errorlevel 1 goto bridge_ready
  timeout /t 1 /nobreak >nul
)
echo WARNING: Web Bridge did not start. Check %BRIDGE_ERR%
if exist "%BRIDGE_ERR%" (
  echo --- Last lines from web_bridge.err.log ---
  powershell -NoProfile -Command "Get-Content -Path '%BRIDGE_ERR%' -Tail 20"
)
:bridge_ready
echo.
echo Starting Web UI at http://localhost:3000
set "NEXT_DISABLE_VERSION_CHECK=1"
set "NEXT_TELEMETRY_DISABLED=1"
npm run dev
echo.
echo Web UI closed.
pause
