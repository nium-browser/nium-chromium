// Nium — what chrome://nium needs from a browser window to show and control its tabs.
// Implemented by the Nium sidebar (nium/browser/ui/views/nium_sidebar_view.cc), which attaches
// itself to the sidebar page's WebContents. This header only depends on //base and //content, so
// the WebUI target does not need to depend on the browser window code.

#ifndef NIUM_BROWSER_UI_WEBUI_NIUM_TABS_BRIDGE_H_
#define NIUM_BROWSER_UI_WEBUI_NIUM_TABS_BRIDGE_H_

#include "base/memory/weak_ptr.h"
#include "base/values.h"

namespace content {
class WebContents;
}

namespace nium {

class TabsBridge {
 public:
  class Listener {
   public:
    virtual void OnTabsChanged() = 0;

   protected:
    virtual ~Listener() = default;
  };

  virtual ~TabsBridge() = default;

  // [{id, title, url, favicon, active, pinned, loading}, ...] in tab order.
  virtual base::ListValue ListTabs() = 0;
  virtual bool ActivateTab(int id) = 0;
  virtual bool CloseTab(int id) = 0;
  virtual void NewTab() = 0;
  virtual bool MoveTab(int id, int to_index) = 0;
  virtual void SetListener(Listener* listener) = 0;
  virtual base::WeakPtr<TabsBridge> GetWeakPtr() = 0;

  // The bridge of the window that hosts `contents` (the sidebar page), or null.
  static TabsBridge* FromWebContents(content::WebContents* contents);
  static void Attach(content::WebContents* contents, TabsBridge* bridge);
};

}  // namespace nium

#endif  // NIUM_BROWSER_UI_WEBUI_NIUM_TABS_BRIDGE_H_
