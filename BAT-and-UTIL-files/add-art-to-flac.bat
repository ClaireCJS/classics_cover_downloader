@Echo OFF

rem We had to move this functionality into a subordinate BAT file after discovering that WinAmp only displays
rem artwork added by Metaflac if you remove the existing artwork first.  So adding requires removing first.



rem Capture parameters and validate environment:
        set PARAMS_ADDARTTOFLAC=%*
        set PARAM_ADDARTTOFLAC_1=%1
        set PARAM_ADDARTTOFLAC_2=%2
        if %VALIDATED_ADDARTTOFLAC ne 1 (
            call validate-in-path remove-art-from-flac add-art-to-flac-helper 
            set VALIDATED_ADDARTTOFLAC=1
        )

rem Remove old art, add new art:
        call remove-art-from-flac                          %PARAM_ADDARTTOFLAC_2%
        call add-art-to-flac-helper %PARAM_ADDARTTOFLAC_1% %PARAM_ADDARTTOFLAC_2%


