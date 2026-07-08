@ECHO OFF
:: dbi-services, 2025
:: created: oliver.schwark@dbi-services.com
:: updated: frank.zeindler@dbi-services.com

TITLE Start OMrun self-test
ECHO.
ECHO *******************************************************
ECHO *   Start OMrun self-test example on batch mode       *
ECHO *******************************************************
ECHO.

SETLOCAL ENABLEDELAYEDEXPANSION
ECHO.
ECHO ::: Start OMrun: OMrun Self-Test: %Date% - %Time%
ECHO.

SET DateToday=%date:~6,4%-%date:~3,2%-%date:~0,2%
SET OMrunPath="%PROGRAMFILES%\dbi\OMrun\OMrun.exe"
SET TAT="%APPDATA%\dbi\OMrun\Example\SelfTest\TestScripts"
SET BSS=OMrun_SelfTest
SET ENV=TestEnvironment1
SET TSC=TestScenario1
SET REP="%APPDATA%\dbi\OMrun\Example\SelfTest\Reports\%DateToday%"
MD  %REP%
SET RET="All"
SET RepMem=5
SET REY="Excel"
SET ROW=-1
SET Log="log\StartOMrun_SelfTest.log"

ECHO ::: OMrunPath = %OMrunPath%
ECHO ::: TAT =       %TAT%
ECHO ::: BSS =       %BSS%
ECHO ::: ENV =       %ENV%
ECHO ::: TSC =       %TSC%
ECHO ::: REP =       %REP%
ECHO ::: RET =       %RET%
ECHO ::: RepMem =    %RepMem%
ECHO ::: REY =       %REY%
ECHO ::: ROW =       %ROW%
REM PAUSE > nul

ECHO Batch Start OMrun TSC=%TSC%: OMrun self-test - Timestamp: %Date% - %Time% >> %Log%

TITLE %ENV%: %BSS% Strecke %TSC%
%OMrunPath% TAT:%TAT% BSS:%BSS% ENV:%ENV% TSC:%TSC% "REP:%REP%" RET:%RET% "REM:%RepMem%" REY:%REY% "ROW:%ROW%"

SET ReturnValue=%ERRORLEVEL%
ECHO.
ECHO ::: End OMrun TSC=%TSC%: OMrun self-test - Timestamp: %Date% - %Time% (ReturnValue = %ReturnValue%)
ECHO Batch End OMrun TSC=%TSC%: OMrun self-test - Timestamp: %Date% - %Time% (ReturnValue = %ReturnValue%) >> %Log%

::: Font color RED if error occurs, otherwise GREEN.
IF %ReturnValue% neq 0 (color 0C&ping -n 3 127.0.0.1 > nul) else (color 0A)
REM PAUSE > nul

EXIT /B %ReturnValue%