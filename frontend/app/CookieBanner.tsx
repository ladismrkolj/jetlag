'use client'

import { useEffect, useState } from 'react'

import { ConsentValue, consentStorageKey, emitConsentChange, readStoredConsent } from './analyticsConsent'

export default function CookieBanner() {
  const [consent, setConsent] = useState<ConsentValue | null>(null)

  useEffect(() => {
    setConsent(readStoredConsent())
  }, [])

  const handleChoice = (value: ConsentValue) => {
    window.localStorage.setItem(consentStorageKey, value)
    setConsent(value)
    emitConsentChange(value)
  }

  if (consent !== null) {
    return null
  }

  return (
    <div className="cookie-banner" role="dialog" aria-live="polite" aria-label="Cookie consent">
      <div className="cookie-banner__content">
        <div className="cookie-banner__text">
          We use analytics cookies to understand site traffic. You can accept or decline analytics cookies.
        </div>
        <div className="cookie-banner__actions">
          <button className="cookie-banner__button" type="button" onClick={() => handleChoice('denied')}>
            Decline
          </button>
          <button className="cookie-banner__button cookie-banner__button--primary" type="button" onClick={() => handleChoice('granted')}>
            Accept
          </button>
        </div>
      </div>
    </div>
  )
}
