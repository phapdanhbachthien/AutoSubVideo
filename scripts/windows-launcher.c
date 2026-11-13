#ifndef UNICODE
#define UNICODE
#endif
#ifndef _UNICODE
#define _UNICODE
#endif
#include <windows.h>
#include <wchar.h>

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous, PWSTR args, int show) {
    (void)instance; (void)previous; (void)show;
    wchar_t root[32768], python[32768], command[32768];
    DWORD length=GetModuleFileNameW(NULL,root,32768);
    if (!length || length>=32768) return 1;
    wchar_t *slash=wcsrchr(root,L'\\');
    if (!slash) return 1;
    *slash=0;
    if (2*wcslen(root)+wcslen(args)+100>=32768) return 1;
    swprintf(python,32768,L"%ls\\python\\pythonw.exe",root);
    swprintf(command,32768,L"\"%ls\" \"%ls\\launch.py\" %ls",python,root,args);
    STARTUPINFOW startup={0}; PROCESS_INFORMATION process={0}; startup.cb=sizeof(startup);
    if (!CreateProcessW(python,command,NULL,NULL,FALSE,CREATE_NO_WINDOW,NULL,root,&startup,&process)) {
        MessageBoxW(NULL,L"Hay giai nen TOAN BO ZIP, roi mo ThienMediaPlayer.exe. Giu thu muc python va player canh executable.",L"Thien Media Player",MB_OK|MB_ICONERROR);
        return 1;
    }
    WaitForSingleObject(process.hProcess,INFINITE);
    DWORD code=1;GetExitCodeProcess(process.hProcess,&code);
    CloseHandle(process.hThread);CloseHandle(process.hProcess);
    if (code) MessageBoxW(NULL,L"Khong khoi dong duoc ung dung. Chay Kiem-tra.cmd; xem log tai %LOCALAPPDATA%\\ThienMediaPlayer\\logs\\startup.log.",L"Thien Media Player",MB_OK|MB_ICONERROR);
    return (int)code;
}
