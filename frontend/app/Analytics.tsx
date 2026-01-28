'use client'

import Script from 'next/script'
import { useEffect, useState } from 'react'

import { consentEventName, readStoredConsent } from './analyticsConsent'

const googleAnalyticsId = 'G-KS1XTLYRTF'

export default function Analytics() {
  const [hasConsent, setHasConsent] = useState(false)

  useEffect(() => {
    const storedConsent = readStoredConsent()
    setHasConsent(storedConsent === 'granted')

    const handleConsentChange = (event: Event) => {
      const detail = (event as CustomEvent).detail
      setHasConsent(detail === 'granted')
    }

    window.addEventListener(consentEventName, handleConsentChange)

    return () => {
      window.removeEventListener(consentEventName, handleConsentChange)
    }
  }, [])

  if (!hasConsent) {
    return null
  }

  return (
    <>
      <Script
        async
        src={`https://www.googletagmanager.com/gtag/js?id=${googleAnalyticsId}`}
        strategy="afterInteractive"
      />
      <Script id="google-analytics" strategy="afterInteractive">
        {`window.dataLayer = window.dataLayer || [];
function gtag(){dataLayer.push(arguments);}
gtag('js', new Date());

gtag('config', '${googleAnalyticsId}');`}
      </Script>
    </>
  )
}
