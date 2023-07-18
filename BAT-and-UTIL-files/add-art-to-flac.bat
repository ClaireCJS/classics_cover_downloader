@echo off


    SET ART=%1
    SET MUSIC=%2
    call validate-environment-variables ART MUSIC


    metaflac --import-picture-from="%@UNQUOTE[%ART]" %MUSIC%


    call warning "this is untested on flac yet - ERRORLEVEL = %ERRORLEVEL% - let's see what happens?!"
    pause



    if ERRORLEVEL 1 (%COLOR_ERROR %+ ECHO %EMOJI_RED_EXCLAMATION_MARK%ERROR embedding art "%ART%" into song "%SONG%"!! %+ BEEP %+ pause %+ pause %+ pause %+ pause %+ pause %+ pause %+ pause %+ pause %+ pause)
REM if ERRORLEVEL 0 .and. %DONT_DELETE_ART_AFTER_EMBEDDING ne 1 (del %ART%)
    if ERRORLEVEL 0 .and. %DONT_DELETE_ART_AFTER_EMBEDDING ne 1 (%COLOR_SUCCESS% %+ echo %EMOJI_CHECK_MARK%Success!!! %+ if %DONT_DELETE_ART_AFTER_EMBEDDING ne 1 (%COLOR_REMOVAL %+ del %ART%))
