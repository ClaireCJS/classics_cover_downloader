@Echo OFF

echo *** About to download cover art...
pause
cover_downloader.py





rem echo .
rem echo .
rem echo .
rem echo .
rem echo .
rem echo *** About to open up cover art download script in notepad...
rem pause
rem notepad get-art.log



echo .
echo .
echo .
echo .
echo .
echo *** About to run cover art download script...
pause
call get-art.bat



echo .
echo .
echo .
echo .
echo .
echo *** Here is where we would go through the art files in an image viewer and delete the incorrect ones, leaving only 1 correct art per song
pause




echo .
echo .
echo .
echo .
echo .
echo *** Here is where we would run wedding_party.py if we wanted to separate the files with art into another folder for some reason
pause



echo .
echo .
echo .
echo .
echo .
echo *** About to run cover_embedder to embed the art into the song files...
cover_embedder.py

