export const consentStorageKey = 'cookie-consent'
export const consentEventName = 'cookie-consent-changed'

export type ConsentValue = 'granted' | 'denied'

export function readStoredConsent(): ConsentValue | null {
  if (typeof window === 'undefined') {
    return null
  }

  const value = window.localStorage.getItem(consentStorageKey)
  if (value === 'granted' || value === 'denied') {
    return value
  }

  return null
}

export function emitConsentChange(value: ConsentValue) {
  if (typeof window === 'undefined') {
    return
  }

  window.dispatchEvent(new CustomEvent(consentEventName, { detail: value }))
}
