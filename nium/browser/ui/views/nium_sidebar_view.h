// Nium — the sidebar on the left of every normal window: a WebView showing
// chrome://nium/sidebar.html, wired to the window's real tabs (TabStripModel).

#ifndef NIUM_BROWSER_UI_VIEWS_NIUM_SIDEBAR_VIEW_H_
#define NIUM_BROWSER_UI_VIEWS_NIUM_SIDEBAR_VIEW_H_

#include "base/memory/raw_ptr.h"
#include "base/memory/weak_ptr.h"
#include "chrome/browser/ui/tabs/tab_strip_model_observer.h"
#include "nium/browser/ui/views/nium_sidebar_mode.h"
#include "nium/browser/ui/webui/nium_tabs_bridge.h"
#include "ui/base/metadata/metadata_header_macros.h"
#include "ui/gfx/geometry/point.h"
#include "ui/views/view.h"

class BrowserWindowInterface;
class TabStripModel;

namespace views {
class WebView;
}

namespace nium {

class NiumSidebarView : public views::View,
                        public TabStripModelObserver,
                        public TabsBridge {
  METADATA_HEADER(NiumSidebarView, views::View)

 public:
  static constexpr int kWidth = 244;
  // Height of the empty strip at the top of the sidebar that drags the window.
  static constexpr int kDragStripHeight = 40;

  explicit NiumSidebarView(BrowserWindowInterface* browser);
  NiumSidebarView(const NiumSidebarView&) = delete;
  NiumSidebarView& operator=(const NiumSidebarView&) = delete;
  ~NiumSidebarView() override;

  // The sidebar among the direct children of `browser_view`, or null.
  static NiumSidebarView* FromBrowserView(views::View* browser_view);

  // True if `point` (in this view's coordinates) should move the window.
  bool IsPositionInWindowCaption(const gfx::Point& point) const;

  // views::View:
  gfx::Size CalculatePreferredSize(
      const views::SizeBounds& available_size) const override;

  // TabStripModelObserver:
  void OnTabStripModelChanged(TabStripModel* tab_strip_model,
                              const TabStripModelChange& change,
                              const TabStripSelectionChange& selection) override;
  void OnTabChangedAt(tabs::TabInterface* tab,
                      TabChangeType change_type) override;
  void OnTabPinnedStateChanged(tabs::TabInterface* tab, int index) override;
  void OnTabStripModelDestroyed(TabStripModel* tab_strip_model) override;

  // TabsBridge:
  base::ListValue ListTabs() override;
  bool ActivateTab(int id) override;
  bool CloseTab(int id) override;
  void NewTab() override;
  bool MoveTab(int id, int to_index) override;
  void SetListener(Listener* listener) override;
  base::WeakPtr<TabsBridge> GetWeakPtr() override;

 private:
  // Index of the tab with this id, or -1.
  int IndexOf(int id) const;
  // Coalesces bursts of changes (a page load fires many) into one update.
  void ScheduleNotify();
  void Notify();

  raw_ptr<BrowserWindowInterface> browser_;
  raw_ptr<TabStripModel> model_;
  raw_ptr<views::WebView> web_view_ = nullptr;
  raw_ptr<Listener> listener_ = nullptr;
  bool notify_pending_ = false;
  base::WeakPtrFactory<NiumSidebarView> weak_factory_{this};
};

}  // namespace nium

#endif  // NIUM_BROWSER_UI_VIEWS_NIUM_SIDEBAR_VIEW_H_
