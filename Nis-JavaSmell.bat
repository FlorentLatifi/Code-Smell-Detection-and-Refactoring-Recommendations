@echo off
rem Nis JavaSmell-in: dosja zgjidhet me dialog dhe shfletuesi hapet vete.
rem Puna e vertete behet nga tools\Nis-JavaSmell.ps1; ky skedar ekziston
rem sepse dy klikime mbi nje .bat jane e vetmja nisje qe nuk kerkon terminal.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\Nis-JavaSmell.ps1"
