rem @echo off
for /F "tokens=1* delims==" %%a in (..\common\.env) do (
    set "%%a=%%b"
)
