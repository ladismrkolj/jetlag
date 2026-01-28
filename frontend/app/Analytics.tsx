'use client'

import Script from 'next/script'

const googleAnalyticsId = 'G-KS1XTLYRTF'

export default function Analytics() {
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
