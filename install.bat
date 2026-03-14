@echo off
setlocal

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

echo [UNLZ AI Studio] Instalando dependencias...

where python >nul 2>&1
if errorlevel 1 (
  echo Python no encontrado. Instalalo y vuelve a ejecutar este script.
  exit /b 1
)

where pip >nul 2>&1
if errorlevel 1 (
  echo pip no encontrado. Instalalo y vuelve a ejecutar este script.
  exit /b 1
)

where winget >nul 2>&1
if errorlevel 0 (
  echo Instalando llama.cpp con winget...
  winget install llama.cpp
) else (
  echo winget no disponible. Omitiendo instalacion de llama.cpp.
)

echo Instalando dependencias Python...
python -m pip install -U fastapi uvicorn httpx psutil python-multipart faster-whisper ^
  lmdeploy huggingface_hub transformers accelerate pillow requests ^
  customtkinter flask flask-socketio SpeechRecognition pyaudio

for /f "tokens=2" %%v in ('python -V 2^>^&1') do set "PY_VER=%%v"
set "PY_VER=%PY_VER:~0,4%"
echo Python detectado: %PY_VER%
if "%PY_VER%"=="3.13" (
  echo [WARN] Python 3.13 puede fallar con algunos backends ^(lmdeploy/vision^). Recomendado: Python 3.11 o 3.12.
)

if "%TORCH_CUDA_TAG%"=="" set "TORCH_CUDA_TAG=cu126"
if "%TORCH_INDEX_URL%"=="" set "TORCH_INDEX_URL=https://download.pytorch.org/whl/%TORCH_CUDA_TAG%"

echo Instalando PyTorch (%TORCH_CUDA_TAG%)...
python -m pip install --index-url "%TORCH_INDEX_URL%" torch torchvision torchaudio
if errorlevel 1 (
  echo [ERROR] Fallo la instalacion de torch con %TORCH_INDEX_URL%.
  echo Revisar driver CUDA y compatibilidad de wheels.
  exit /b 1
)

echo Verificando Torch/CUDA...
python -c "import torch; print('torch=',torch.__version__,' cuda_runtime=',torch.version.cuda,' cuda_available=',torch.cuda.is_available())"
python -c "import sys, torch; sys.exit(0 if torch.cuda.is_available() else 1)"
if errorlevel 1 (
  echo [WARN] Torch quedo en CPU ^(cuda_available=False^).
  echo [WARN] Reinstala con:
  echo        python -m pip install --index-url https://download.pytorch.org/whl/cu126 torch torchvision torchaudio
)

if exist "system\\web_ui\\package.json" (
  echo Instalando dependencias Web UI...
  pushd "system\\web_ui"
  call npm install
  popd
) else (
  echo No se encontro system\\web_ui\\package.json. Omitiendo npm install.
)

echo Listo.
endlocal
