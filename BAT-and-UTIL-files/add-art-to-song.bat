@echo off
SET ART=%1
SET SONG=%2
call validate-environment-variables ART SONG

iff     "%@ext[%SONG%]" == "mp3" then
    call add-art-to-mp3.bat  %ART% %SONG% %3 %4 %5 %6 %7 %8 %9
elseiff "%@ext[%SONG%]" == "flac" then
    call add-art-to-flac.bat %ART% %SONG% %3 %4 %5 %6 %7 %8 %9
else
    %COLOR_ERROR% 
    echo WTF EXTENSION IS %@EXT[%SONG%]!?!?!?!
    pause
    pause
    pause
    pause
    pause
endiff

%COLOR_SUCCESS%
echo Done!
