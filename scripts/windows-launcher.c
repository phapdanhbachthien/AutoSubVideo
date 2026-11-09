#ifndef UNICODE
#define UNICODE
#endif
#ifndef _UNICODE
#define _UNICODE
#endif
#include <windows.h>
#include <wchar.h>

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous, PWSTR cmd, int show) {
    (void)instance; (void)previous; (void)cmd; (void)show;
    wchar_t root[32768], python[32768], script[32768], command[32768], tcl[32768];
    DWORD size = GetModuleFileNameW(NULL, root, 32768);
    if (!size || size >= 32768) return 1;
    wchar_t *slash = wcsrchr(root, L'\\');
    if (!slash) return 1;
    *slash = 0;
    if (wcslen(root) > 15000) return 1;
    swprintf(python, 32768, L"%ls\\python\\pythonw.exe", root);
    swprintf(script, 32768, L"%ls\\launch.py", root);
    swprintf(command, 32768, L"\"%ls\" \"%ls\"", python, script);
    swprintf(tcl, 32768, L"%ls\\python\\tcl\\tcl8.6", root);
    SetEnvironmentVariableW(L"TCL_LIBRARY", tcl);
    swprintf(tcl, 32768, L"%ls\\python\\tcl\\tk8.6", root);
    SetEnvironmentVariableW(L"TK_LIBRARY", tcl);
    STARTUPINFOW startup = {0};
    PROCESS_INFORMATION process = {0};
    startup.cb = sizeof(startup);
    if (!CreateProcessW(python, command, NULL, NULL, FALSE, CREATE_NO_WINDOW,
                        NULL, root, &startup, &process)) {
        MessageBoxW(NULL, L"Khong khoi dong duoc Python di kem. Hay giai nen TOAN BO goi ZIP, roi mo AutoSubVideo.exe trong thu muc da giai nen.",
                    L"AutoSubVideo", MB_OK | MB_ICONERROR);
        return 1;
    }
    WaitForSingleObject(process.hProcess, INFINITE);
    DWORD exit_code = 1;
    GetExitCodeProcess(process.hProcess, &exit_code);
    CloseHandle(process.hThread);
    CloseHandle(process.hProcess);
    if (exit_code != 0) {
        MessageBoxW(NULL, L"Ung dung gap loi. Xem startup.log trong %LOCALAPPDATA%\\AutoSubVideo\\logs. Giu nguyen cac thu muc python, autosub va bundle canh file exe.",
                    L"AutoSubVideo", MB_OK | MB_ICONERROR);
    }
    return (int)exit_code;
}
