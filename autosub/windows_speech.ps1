param([Parameter(Mandatory=$true)][string]$RequestPath)
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName System.Speech
$request = Get-Content -LiteralPath $RequestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$speaker = [System.Speech.Synthesis.SpeechSynthesizer]::new()
try {
    if ($request.action -eq "voices") {
        $voices = @($speaker.GetInstalledVoices() | Where-Object { $_.Enabled } | ForEach-Object {
            @{ id = $_.VoiceInfo.Name; locale = $_.VoiceInfo.Culture.Name; gender = $_.VoiceInfo.Gender.ToString() }
        })
        ConvertTo-Json -InputObject $voices -Compress
    } elseif ($request.action -eq "speak") {
        $speaker.SelectVoice([string]$request.voice)
        $speaker.Rate = [Math]::Max(-10, [Math]::Min(10, [int]([double]$request.rate / 10)))
        $speaker.SetOutputToWaveFile([string]$request.output)
        $speaker.Speak([string]$request.text)
    } else {
        throw "Unknown action"
    }
} finally {
    $speaker.Dispose()
}
