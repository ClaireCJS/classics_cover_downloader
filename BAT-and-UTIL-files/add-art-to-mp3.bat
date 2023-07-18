@echo off

REM set this to 1 to use TagEdit.exe in the event that eyeD3.ee fails:
set USE_FALLBACK_EMBEDDING_METHOD=0

REM check parameters
SET ART=%1
SET MUSIC=%2
SET THREE=%@UPPER[%3]
if "%THREE%" eq "ALT" .or. "%THREE%" eq "ALTERNATE" (goto :Alt_Yes)


REM embed the art into the song
echo eyed3.exe --add-image="%@UNQUOTE[%ART]:FRONT_COVER" %MUSIC% 
     eyed3.exe --add-image="%@UNQUOTE[%ART]:FRONT_COVER" %MUSIC% 
set EYE3DERRORLEVEL=%_?
 %COLOR_UNIMPORTANT% %+ echo EYE3DERRORLEVEL  is %EYE3DERRORLEVEL%  %+ %COLOR_NORMAL

if %EYE3DERRORLEVEL% == 1 .and. %USE_FALLBACK_EMBEDDING_METHOD% == 0 (%COLOR_ERROR%   %+ echo ERROR embedding art "%ART%" into song "%SONG%"!! %+ BEEP %+ pause %+ pause %+ pause %+ pause %+ pause %+ pause %+ pause %+ pause %+ pause)
if %EYE3DERRORLEVEL% == 1 .and. %USE_FALLBACK_EMBEDDING_METHOD% == 1 (goto :Do_Alt_Method_Due_To_Primary_Failure)



REM this stuff eventually worked but we decided not to go with it:
goto :Alt_No
            :Do_Alt_Method_Due_To_Primary_Failure
                    %COLOR_WARNING% %+ echo * Embedding with eyed3.exe failed, using TagEditor.exe instead! %+ %COLOR_NORMAL%
            :Alt_Yes
                    %COLOR_WARNING% %+ echo ------- Embedding using alternate method, which will screw up our command line afterward, so I'm pausing first and will launch it in another window ------- %+ pause %+ %COLOR_NORMAL%
                    REM can also use tageditor --print-field-names
                    tageditor set cover=":front-cover" cover0="%@UNQUOTE[%ART]:front-cover:front cover"                           -f %MUSIC%
                    REM echo example 1) tageditor set cover=":front-cover" cover0="%@UNQUOTE[%ART]"                                                   -f %MUSIC%
                    REM echo example 2) tageditor set cover=":front-cover" cover0="%@UNQUOTE[%ART]:front-cover:front cover"                           -f %MUSIC%
                    REM echo example 3) tageditor set cover=":front-cover" cover0="%@UNQUOTE[%ART]:front-cover:front cover" id3:PRIV=\0               -f %MUSIC% 
                    REM echo example 4) tageditor set cover=":front-cover" cover0="%@UNQUOTE[%ART]:front-cover:front cover" id3:PRIV±>=%NULLBYTEFILE% -f %MUSIC% 
                    REM REM echo Doing example 4:                tageditor set cover=":front-cover" cover0="%@UNQUOTE[%ART]:front-cover:front cover" id3:PRIV±>=%NULLBYTEFILE% -f %MUSIC% 
                    REM echo example 5) tageditor set cover=":front-cover" cover0="%@UNQUOTE[%ART]:front-cover:front cover" id3:PRIV=null             -f %MUSIC% 
                    REM REM Example 3:
                    REM REM  tageditor set cover=":front-cover" cover0="Zez Confrey - Kitten On The Keys (1921).jpg:front-cover:front cover" id3:PRIV= -f "Zez Confrey - Kitten On The Keys (1921).mp3"
                    REM REM - Changes have been applied.
                    REM REM  - Diagnostic messages:
                    REM REM     Error        14:33:07   setting tags: Unable set field "PRIV": setting field is not supported
                    REM REM     Error        14:33:07   setting tags: Unable set field "Cover": setting field is not supported
                    REM REM   but it is set and works in winamp and verified with the creator of TagRename.exe that these are false error messages
            :Alt_No


if ERRORLEVEL 1 (%COLOR_ERROR%   %+ echo %EMOJI_RED_EXCLAMATION_MARK%%ERROR embedding art "%ART%" into song "%SONG%"!! %+ BEEP %+ pause %+ pause %+ pause %+ pause %+ pause %+ pause %+ pause %+ pause %+ pause)
if ERRORLEVEL 0 (%COLOR_SUCCESS% %+ echo %EMOJI_CHECK_MARK%Success!!! %+ if %DONT_DELETE_ART_AFTER_EMBEDDING ne 1 (%COLOR_REMOVAL %+ del %ART%))


%COLOR_NORMAL%
