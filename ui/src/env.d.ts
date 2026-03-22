interface Window {
    electron?: {
        appVersion: () => Promise<string>
    }
}
