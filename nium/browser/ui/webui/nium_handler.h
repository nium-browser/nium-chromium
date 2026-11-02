// Nium — the native side of window.nium: chrome.send('nium.call', [id, method, params]).

#ifndef NIUM_BROWSER_UI_WEBUI_NIUM_HANDLER_H_
#define NIUM_BROWSER_UI_WEBUI_NIUM_HANDLER_H_

#include <string>

#include "base/files/file_path.h"
#include "base/memory/weak_ptr.h"
#include "base/values.h"
#include "content/public/browser/web_ui_message_handler.h"
#include "nium/browser/ui/webui/nium_tabs_bridge.h"

namespace nium {

class NiumHandler : public content::WebUIMessageHandler,
                    public TabsBridge::Listener {
 public:
  explicit NiumHandler(base::FilePath store_dir);
  NiumHandler(const NiumHandler&) = delete;
  NiumHandler& operator=(const NiumHandler&) = delete;
  ~NiumHandler() override;

  // content::WebUIMessageHandler:
  void RegisterMessages() override;
  void OnJavascriptDisallowed() override;

  // TabsBridge::Listener:
  void OnTabsChanged() override;

 private:
  void HandleCall(const base::ListValue& args);
  // Tab methods ("tabs.*"); returns false if `method` is not one of them.
  bool HandleTabsCall(base::Value& id, const std::string& method,
                      const base::DictValue* params);
  TabsBridge* Tabs();
  void StopWatchingTabs();
  void Reply(base::Value callback_id, bool ok, base::Value result);
  void ReplyValue(base::Value callback_id, base::Value result);
  void ReplyBool(base::Value callback_id, bool ok);

  const base::FilePath store_dir_;
  base::WeakPtr<TabsBridge> tabs_;
  bool watching_tabs_ = false;
  base::WeakPtrFactory<NiumHandler> weak_factory_{this};
};

}  // namespace nium

#endif  // NIUM_BROWSER_UI_WEBUI_NIUM_HANDLER_H_
