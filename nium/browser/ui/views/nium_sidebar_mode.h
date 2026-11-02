// Nium — whether a window uses the Nium sidebar instead of Chromium's tab strip.
// Header-only on purpose: the patched Chromium files include it without new build deps.

#ifndef NIUM_BROWSER_UI_VIEWS_NIUM_SIDEBAR_MODE_H_
#define NIUM_BROWSER_UI_VIEWS_NIUM_SIDEBAR_MODE_H_

#include "base/command_line.h"
#include "chrome/browser/ui/browser_window/public/browser_window_interface.h"

namespace nium {

// Start with --nium-classic-tabs to get Chromium's own tab strip back (for comparing/debugging).
inline constexpr char kNiumClassicTabsSwitch[] = "nium-classic-tabs";

inline bool NiumSidebarEnabled(const BrowserWindowInterface* browser) {
  return browser && browser->GetType() == BrowserWindowInterface::TYPE_NORMAL &&
         !base::CommandLine::ForCurrentProcess()->HasSwitch(kNiumClassicTabsSwitch);
}

}  // namespace nium

#endif  // NIUM_BROWSER_UI_VIEWS_NIUM_SIDEBAR_MODE_H_
