// Nium — see nium_tabs_bridge.h.

#include "nium/browser/ui/webui/nium_tabs_bridge.h"

#include <memory>
#include <utility>

#include "base/supports_user_data.h"
#include "content/public/browser/web_contents.h"

namespace nium {

namespace {

const char kTabsBridgeKey[] = "nium-tabs-bridge";

class Holder : public base::SupportsUserData::Data {
 public:
  explicit Holder(base::WeakPtr<TabsBridge> bridge) : bridge_(std::move(bridge)) {}
  TabsBridge* get() const { return bridge_.get(); }

 private:
  base::WeakPtr<TabsBridge> bridge_;
};

}  // namespace

// static
TabsBridge* TabsBridge::FromWebContents(content::WebContents* contents) {
  if (!contents) {
    return nullptr;
  }
  auto* holder = static_cast<Holder*>(contents->GetUserData(kTabsBridgeKey));
  return holder ? holder->get() : nullptr;
}

// static
void TabsBridge::Attach(content::WebContents* contents, TabsBridge* bridge) {
  contents->SetUserData(kTabsBridgeKey,
                        std::make_unique<Holder>(bridge->GetWeakPtr()));
}

}  // namespace nium
