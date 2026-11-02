// Nium — see nium_sidebar_view.h.

#include "nium/browser/ui/views/nium_sidebar_view.h"

#include <algorithm>
#include <memory>
#include <string>

#include "base/functional/bind.h"
#include "base/strings/utf_string_conversions.h"
#include "base/task/single_thread_task_runner.h"
#include "chrome/browser/profiles/profile.h"
#include "chrome/browser/ui/browser_commands.h"
#include "chrome/browser/ui/browser_window/public/browser_window_interface.h"
#include "chrome/browser/ui/tabs/tab_enums.h"
#include "chrome/browser/ui/tabs/tab_strip_model.h"
#include "chrome/browser/ui/tabs/tab_strip_user_gesture_details.h"
#include "components/tabs/public/tab_interface.h"
#include "content/public/browser/favicon_status.h"
#include "content/public/browser/navigation_controller.h"
#include "content/public/browser/navigation_entry.h"
#include "content/public/browser/web_contents.h"
#include "ui/base/metadata/metadata_impl_macros.h"
#include "ui/base/webui/web_ui_util.h"
#include "ui/gfx/image/image.h"
#include "ui/views/controls/webview/webview.h"
#include "ui/views/layout/fill_layout.h"
#include "ui/views/view_utils.h"
#include "url/gurl.h"

namespace nium {

namespace {

constexpr char kSidebarUrl[] = "chrome://nium/sidebar.html";

std::string FaviconDataUrl(content::WebContents* contents) {
  content::NavigationEntry* entry =
      contents->GetController().GetLastCommittedEntry();
  if (!entry) {
    return std::string();
  }
  const content::FaviconStatus& favicon = entry->GetFavicon();
  if (!favicon.valid || favicon.image.IsEmpty()) {
    return std::string();
  }
  return webui::GetBitmapDataUrl(favicon.image.AsBitmap());
}

}  // namespace

NiumSidebarView::NiumSidebarView(BrowserWindowInterface* browser)
    : browser_(browser), model_(browser->GetTabStripModel()) {
  SetLayoutManager(std::make_unique<views::FillLayout>());
  web_view_ = AddChildView(
      std::make_unique<views::WebView>(browser->GetProfile()));
  content::WebContents* contents = web_view_->GetWebContents();
  TabsBridge::Attach(contents, this);
  model_->AddObserver(this);
  web_view_->LoadInitialURL(GURL(kSidebarUrl));
}

NiumSidebarView::~NiumSidebarView() {
  listener_ = nullptr;
  weak_factory_.InvalidateWeakPtrs();
  if (model_) {
    model_->RemoveObserver(this);
  }
}

// static
NiumSidebarView* NiumSidebarView::FromBrowserView(views::View* browser_view) {
  if (!browser_view) {
    return nullptr;
  }
  for (views::View* child : browser_view->children()) {
    if (auto* sidebar = views::AsViewClass<NiumSidebarView>(child)) {
      return sidebar;
    }
  }
  return nullptr;
}

bool NiumSidebarView::IsPositionInWindowCaption(const gfx::Point& point) const {
  return GetVisible() && point.x() >= 0 && point.x() < width() &&
         point.y() >= 0 && point.y() < kDragStripHeight;
}

gfx::Size NiumSidebarView::CalculatePreferredSize(
    const views::SizeBounds& available_size) const {
  return gfx::Size(kWidth, 0);
}

void NiumSidebarView::OnTabStripModelChanged(
    TabStripModel* tab_strip_model,
    const TabStripModelChange& change,
    const TabStripSelectionChange& selection) {
  ScheduleNotify();
}

void NiumSidebarView::OnTabChangedAt(tabs::TabInterface* tab,
                                     TabChangeType change_type) {
  ScheduleNotify();
}

void NiumSidebarView::OnTabPinnedStateChanged(tabs::TabInterface* tab,
                                              int index) {
  ScheduleNotify();
}

void NiumSidebarView::OnTabStripModelDestroyed(TabStripModel* tab_strip_model) {
  if (tab_strip_model == model_) {
    model_ = nullptr;
  }
}

base::ListValue NiumSidebarView::ListTabs() {
  base::ListValue list;
  if (!model_) {
    return list;
  }
  const int active = model_->active_index();
  for (int i = 0; i < model_->count(); ++i) {
    tabs::TabInterface* tab = model_->GetTabAtIndex(i);
    content::WebContents* contents = tab ? tab->GetContents() : nullptr;
    if (!contents) {
      continue;
    }
    const GURL& url = contents->GetVisibleURL();
    std::string title = base::UTF16ToUTF8(contents->GetTitle());
    if (title.empty()) {
      title = url.spec();
    }
    base::DictValue item;
    item.Set("id", tab->GetHandle().raw_value());
    item.Set("title", title);
    item.Set("url", url.spec());
    item.Set("favicon", FaviconDataUrl(contents));
    item.Set("active", i == active);
    item.Set("pinned", model_->IsTabPinned(i));
    item.Set("loading", contents->IsLoading());
    list.Append(std::move(item));
  }
  return list;
}

int NiumSidebarView::IndexOf(int id) const {
  if (!model_) {
    return -1;
  }
  for (int i = 0; i < model_->count(); ++i) {
    tabs::TabInterface* tab = model_->GetTabAtIndex(i);
    if (tab && tab->GetHandle().raw_value() == id) {
      return i;
    }
  }
  return -1;
}

bool NiumSidebarView::ActivateTab(int id) {
  const int index = IndexOf(id);
  if (index < 0) {
    return false;
  }
  model_->ActivateTabAt(index, TabStripUserGestureDetails(
                                   TabStripUserGestureDetails::GestureType::kMouse));
  return true;
}

bool NiumSidebarView::CloseTab(int id) {
  const int index = IndexOf(id);
  if (index < 0) {
    return false;
  }
  model_->CloseWebContentsAt(index, TabCloseTypes::CLOSE_USER_GESTURE |
                                        TabCloseTypes::CLOSE_CREATE_HISTORICAL_TAB);
  return true;
}

void NiumSidebarView::NewTab() {
  chrome::NewTab(browser_, NewTabTypes::kNewTabButton);
}

bool NiumSidebarView::MoveTab(int id, int to_index) {
  const int index = IndexOf(id);
  if (index < 0) {
    return false;
  }
  // Pinned tabs stay before the others; a move never crosses that boundary.
  const int first_unpinned = model_->IndexOfFirstNonPinnedTab();
  const bool pinned = model_->IsTabPinned(index);
  const int low = pinned ? 0 : first_unpinned;
  const int high = pinned ? first_unpinned - 1 : model_->count() - 1;
  to_index = std::clamp(to_index, low, std::max(low, high));
  if (to_index != index) {
    model_->MoveWebContentsAt(index, to_index, /*select_after_move=*/false);
  }
  return true;
}

void NiumSidebarView::SetListener(Listener* listener) {
  listener_ = listener;
}

base::WeakPtr<TabsBridge> NiumSidebarView::GetWeakPtr() {
  return weak_factory_.GetWeakPtr();
}

void NiumSidebarView::ScheduleNotify() {
  if (notify_pending_ || !listener_) {
    return;
  }
  notify_pending_ = true;
  base::SingleThreadTaskRunner::GetCurrentDefault()->PostTask(
      FROM_HERE, base::BindOnce(&NiumSidebarView::Notify,
                                weak_factory_.GetWeakPtr()));
}

void NiumSidebarView::Notify() {
  notify_pending_ = false;
  if (listener_) {
    listener_->OnTabsChanged();
  }
}

BEGIN_METADATA(NiumSidebarView)
END_METADATA

}  // namespace nium
