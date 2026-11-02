// Nium — chrome://nium serves the Nium interface and exposes the native bridge.

#ifndef NIUM_BROWSER_UI_WEBUI_NIUM_UI_H_
#define NIUM_BROWSER_UI_WEBUI_NIUM_UI_H_

#include "content/public/browser/web_ui_controller.h"
#include "content/public/browser/webui_config.h"
#include "content/public/common/url_constants.h"

namespace nium {

inline constexpr char kNiumHost[] = "nium";
// Folder with the interface files. Without it, Nium looks in <exe>\nium_ui (installed build)
// and then in src\nium\ui (development build in src\out\<name>).
inline constexpr char kNiumUiDirSwitch[] = "nium-ui-dir";

class NiumUI;

class NiumUIConfig : public content::DefaultWebUIConfig<NiumUI> {
 public:
  NiumUIConfig()
      : DefaultWebUIConfig(content::kChromeUIScheme, kNiumHost) {}
};

class NiumUI : public content::WebUIController {
 public:
  explicit NiumUI(content::WebUI* web_ui);
  NiumUI(const NiumUI&) = delete;
  NiumUI& operator=(const NiumUI&) = delete;
  ~NiumUI() override;
};

}  // namespace nium

#endif  // NIUM_BROWSER_UI_WEBUI_NIUM_UI_H_
