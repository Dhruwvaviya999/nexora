import * as React from "react"

const MOBILE_BREAKPOINT = 768
const QUERY = `(max-width: ${MOBILE_BREAKPOINT - 1}px)`

function subscribe(onChange: () => void) {
  const mql = window.matchMedia(QUERY)
  mql.addEventListener("change", onChange)
  return () => mql.removeEventListener("change", onChange)
}

/**
 * True below the mobile breakpoint.
 *
 * Reads the media query through `useSyncExternalStore` so the first client
 * render already has the right answer -- an effect that set state after mount
 * would render the desktop layout for a frame on every phone.
 */
export function useIsMobile() {
  return React.useSyncExternalStore(
    subscribe,
    () => window.matchMedia(QUERY).matches,
    // The server has no viewport; assume desktop, as the old effect-based
    // version did before it had run.
    () => false
  )
}
